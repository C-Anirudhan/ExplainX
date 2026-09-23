import sys
if sys.stdout and hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass
if sys.stderr and hasattr(sys.stderr, 'reconfigure'):
    try:
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

import os
os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"
os.environ["TRANSFORMERS_FORCE_SAFE_LOADING"] = "1"
os.environ["HF_HUB_DISABLE_TELEMETRY"] = "1"
os.environ["HF_HUB_ENABLE_HF_TRANSFER"] = "0"
os.environ["ANONYMIZED_TELEMETRY"] = "False"
os.environ["CHROMA_TELEMETRY"] = "False"
os.environ["CHROMA_TELEMETRY_IMPL"] = "None"

# Ensure imageio_ffmpeg's bundled ffmpeg is on PATH for subprocess calls
try:
    import imageio_ffmpeg
    _ffmpeg_dir = os.path.dirname(imageio_ffmpeg.get_ffmpeg_exe())
    if _ffmpeg_dir not in os.environ.get("PATH", ""):
        os.environ["PATH"] = _ffmpeg_dir + os.pathsep + os.environ.get("PATH", "")
except ImportError:
    pass

import logging
logging.getLogger("chromadb").setLevel(logging.ERROR)
logging.getLogger("chromadb.telemetry.product.posthog").setLevel(logging.ERROR)


from fastapi import FastAPI, UploadFile, File, Form, Depends, HTTPException, Header, Request
from fastapi.responses import FileResponse, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uuid, shutil, json
from datetime import datetime

# Import your custom modules
from process_ppt import Ppt2Pdf
from pdf_ppt_extract import Pdf2Json
from pdf_chroma_ingest import ChromaMultimodalDB
from download_video import VideoDownloader
from detect_video_audio import gen_json
from ingest_and_query_chroma import VectorDB
from ExplainX_LLM import LLM
from web_scrapper import FullPageExtractor

from mongo import users_col, sessions_col, content_details_col
from auth_utils import hash_password, verify_password, create_access_token, decode_token

app = FastAPI()
app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"]
)

UPLOAD_DIR = "downloads/"
os.makedirs(UPLOAD_DIR, exist_ok=True)

video_extensions = {
    ".mp4",".m4v",".mov",".avi",".mkv",".webm",".flv",".wmv",".mpg",".mpeg",".3gp",".3g2",".ts",".mts",".m2ts",
    ".vob",".ogv",".f4v",".rm",".rmvb",".asf",".divx",".xvid",".dv",".amv",".yuv"
}

# ============================================================
# AUTH
# ============================================================

class SignupRequest(BaseModel):
    email: str
    username: str
    password: str

class LoginRequest(BaseModel):
    email: str
    password: str

class LinkUpload(BaseModel):
    session_id: str
    video_link: str

class AskRequest(BaseModel):
    session_id: str
    question: str

def get_current_user(request: Request, authorization: str = Header(None)):
    if request.method == "OPTIONS":
        return None
    if not authorization:
        # Fallback to guest user for seamless demo / test access
        guest = users_col.find_one({"email": "guest@explainx.ai"})
        if not guest:
            guest = {
                "email": "guest@explainx.ai",
                "username": "Guest User",
                "password_hash": "guest_pass",
                "created_at": datetime.utcnow()
            }
            users_col.insert_one(guest)
        return guest
    try:
        parts = authorization.split()
        token = parts[1] if len(parts) > 1 else parts[0]
        payload = decode_token(token)
        email = payload["sub"]
    except Exception:
        guest = users_col.find_one({"email": "guest@explainx.ai"})
        if guest:
            return guest
        raise HTTPException(401, "Invalid token")
    user = users_col.find_one({"email": email})
    if not user:
        raise HTTPException(401, "User not found")
    return user

# ============================================================
# AUTH ROUTES
# ============================================================

@app.post("/api/signup")
def signup(req: SignupRequest):
    if users_col.find_one({"email": req.email}):
        raise HTTPException(400, "Email exists")
    users_col.insert_one({
        "email": req.email,
        "username": req.username,
        "password_hash": hash_password(req.password),
        "created_at": datetime.utcnow()
    })
    return {"message": "User created"}

@app.post("/api/login")
def login(req: LoginRequest):
    user = users_col.find_one({"email": req.email})
    if not user or not verify_password(req.password, user["password_hash"]):
        raise HTTPException(400, "Invalid credentials")
    token = create_access_token({"sub": user["email"]})
    return {"access_token": token, "token_type": "bearer",
            "user": {"name": user["username"], "email": user["email"]}}

@app.post("/api/me")
def api_me(current_user=Depends(get_current_user)):
    return {"name": current_user["username"], "email": current_user["email"]}

class ProfileUpdateRequest(BaseModel):
    username: str = None
    email: str = None
    apiKey: str = None

@app.get("/api/settings/status")
def get_settings_status():
    groq_key = os.getenv("GROQ_API_KEY")
    gemini_key = os.getenv("GEMINI_API_KEY") or os.getenv("API")
    generic_key = os.getenv("API_KEY")
    if generic_key:
        if generic_key.startswith("gsk_"):
            groq_key = groq_key or generic_key
        else:
            gemini_key = gemini_key or generic_key

    if groq_key:
        return {
            "llm_active": True,
            "provider": "Groq",
            "model": "llama-3.3-70b-versatile"
        }
    elif gemini_key:
        return {
            "llm_active": True,
            "provider": "Google Gemini",
            "model": "gemini-2.5-flash"
        }
    else:
        return {
            "llm_active": False,
            "provider": None,
            "model": "offline-fallback"
        }

@app.post("/api/settings/profile")
def update_profile(req: ProfileUpdateRequest, current_user=Depends(get_current_user)):
    user_email = current_user.get("email", "guest@explainx.ai")
    updates = {}
    if req.username:
        updates["username"] = req.username
    if req.email and req.email != user_email:
        updates["email"] = req.email
    if updates:
        users_col.update_one({"email": user_email}, {"$set": updates})

    if req.apiKey and req.apiKey.strip():
        key = req.apiKey.strip()
        env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
        if key.startswith("gsk_"):
            os.environ["GROQ_API_KEY"] = key
            try:
                with open(env_path, "w", encoding="utf-8") as f:
                    f.write(f"GROQ_API_KEY={key}\n")
            except Exception as e:
                print(f"[WARN] Failed to write .env: {e}")
        else:
            os.environ["GEMINI_API_KEY"] = key
            os.environ["API"] = key
            try:
                with open(env_path, "w", encoding="utf-8") as f:
                    f.write(f"GEMINI_API_KEY={key}\nAPI={key}\n")
            except Exception as e:
                print(f"[WARN] Failed to write .env: {e}")

    updated_user = users_col.find_one({"email": updates.get("email", user_email)}) or current_user
    status = get_settings_status()
    return {
        "message": f"Settings updated successfully. Active engine: {status.get('provider', 'Offline')} ({status['model']}).",
        "user": {
            "name": updated_user.get("username", "User"),
            "email": updated_user.get("email", user_email)
        },
        "llm_active": status["llm_active"],
        "provider": status.get("provider"),
        "model": status["model"]
    }

# ============================================================
# SESSIONS
# ============================================================

@app.post("/api/new-session")
def new_session(current_user=Depends(get_current_user)):

    sessions_col.delete_many({
        "user_email": current_user["email"],
        "files": {"$eq": []} 
    })
    
    sid = str(uuid.uuid4())
    sessions_col.insert_one({
        "_id": sid,
        "user_email": current_user["email"],
        "files": [],
        "messages": [],
        "created_at": datetime.utcnow()
    })
    return {"session_id": sid}

@app.post("/api/sessions")
def create_session_alias(current_user=Depends(get_current_user)):
    return new_session(current_user)

# In server.py / newserver.py

@app.get("/api/sessions")
def api_sessions(current_user=Depends(get_current_user)):
    res = []
    
    '''sessions_col.delete_many({
        "user_email": current_user["email"],
        "files": {"$eq": []} 
    })'''

    # Fetch sessions for the user
    user_sessions = sessions_col.find({"user_email": current_user["email"]}).sort("created_at", -1)
    
    for s in user_sessions:
        # safely find the first user message for the title
        messages = s.get("messages", [])
        
        # FIX: We filter specifically for DICTIONARIES to avoid the TypeError
        first_user_msg = next(
            (m for m in messages if isinstance(m, dict) and m.get("role") == "user"), 
            None
        )
        
        if first_user_msg and "text" in first_user_msg:
            title = first_user_msg["text"][:40]
        else:
            title = "New Conversation"

        # Enrich files with real_name and uuid
        enriched_files = []
        for f in s.get("files", []):
            fname = f.get("name", "")
            fext = f.get("ext", "")
            det = content_details_col.find_one({"base_uuid": fname})
            if not det:
                det = content_details_col.find_one({"uuid": fname})
            if not det:
                det = content_details_col.find_one({"real_name": fname})
            real_n = det.get("real_name") if det else fname
            base_u = det.get("base_uuid") if det else fname
            src_u = det.get("source_url") if det else None
            is_vid = (
                fext.lower() in video_extensions or 
                (det and det.get("content_type", "").lower() in video_extensions) or 
                any(fname.lower().endswith(ve) for ve in video_extensions) or 
                any(real_n.lower().endswith(ve) for ve in video_extensions) or 
                ("youtube.com" in real_n.lower() or "youtu.be" in real_n.lower())
            )
            enriched_files.append({
                "name": real_n,
                "uuid": base_u,
                "ext": fext,
                "type": "video" if is_vid else "document",
                "source_url": src_u or (real_n if ("youtube.com" in real_n.lower() or "youtu.be" in real_n.lower()) else None)
            })

        res.append({
            "id": s["_id"], 
            "title": title, 
            "timestamp": s["created_at"], 
            "files": enriched_files
        })
    
    return res

# ============================================================
# PIPELINES
# ============================================================

def process_video_pipeline(session_id, user_email, input_path, ext):
    filename = os.path.basename(input_path)
    
    # Run ingestion logic
    gen_json(filename).main()
    VectorDB(filename).ingest_json()
    summary = LLM().summarize_video(filename)
    
    # FIX: Merged duplicate "$push" keys into one dictionary
    sessions_col.update_one(
        {"_id": session_id},
        {
            "$push": {
                "files": {"name": filename, "ext": ext},
                "messages": {"role": "assistant", "text": summary, "time": datetime.utcnow()}
            }
        }
    )
    return summary

def process_pdf_ppt_pipeline(session_id, user_email, input_path, ext):
    filename = os.path.basename(input_path)
    
    # Run ingestion logic
    Pdf2Json(filename).extract()
    ChromaMultimodalDB(session_id, filename).ingest_text()
    
    # Even without a summary, we must confirm upload to the user and DB
    msg_text = "Document Uploaded Successfully..."
    
    # FIX: Merged duplicate "$push" keys into one dictionary
    sessions_col.update_one(
        {"_id": session_id},
        {
            "$push": {
                "files": {"name": filename, "ext": ext},
                "messages": {"role": "assistant", "text": msg_text, "time": datetime.utcnow()}
            }
        }
    )
    return msg_text

# ============================================================
# UPLOAD
# ============================================================

@app.post("/api/upload/file")
def upload_file(session_id: str = Form(...), file: UploadFile = File(...), current_user=Depends(get_current_user)):
    session = sessions_col.find_one({"_id":session_id,"user_email":current_user["email"]})
    if not session: raise HTTPException(403,"Invalid session")

    ext = os.path.splitext(file.filename)[1].lower()
    generated_uuid = str(uuid.uuid4())
    path = os.path.join(UPLOAD_DIR,f"{generated_uuid}{ext}")
    
    with open(path,"wb") as f: shutil.copyfileobj(file.file,f)
    
    # Store content details for real filename lookup
    content_details_col.insert_one({
        "uuid": f"{generated_uuid}{ext}",
        "base_uuid": generated_uuid,
        "real_name": file.filename,
        "session_id": session_id,
        "user_email": current_user["email"],
        "content_type": ext,
        "uploaded_at": datetime.utcnow()
    })

    if ext in video_extensions:
        summary = process_video_pipeline(session_id, current_user["email"], path, ext)
    
    elif ext in [".pdf",".ppt",".pptx"]:
        # FIX: Use splitext to safely get the base path (handles .pptx correctly)
        base_path = os.path.splitext(path)[0]
        
        if ext != ".pdf":
            # Convert PPT to PDF
            Ppt2Pdf(base_path, ext[1:]).convert_ppt_to_pdf()
        
        # Pass the base path (without extension) to the pipeline
        summary = process_pdf_ppt_pipeline(session_id, current_user["email"], base_path, ext)
    
    else:
        raise HTTPException(400,"Unsupported")

    return {
        "summary": summary,
        "uuid": generated_uuid,
        "filename": file.filename,
        "ext": ext
    }

# ============================================================
# ASK + HISTORY
# ============================================================

@app.post("/api/ask")
def api_ask(req: AskRequest, current_user=Depends(get_current_user)):
    # 1. Validate Session
    session = sessions_col.find_one({"_id": req.session_id, "user_email": current_user["email"]})
    if not session:
        raise HTTPException(403, "Invalid session")

    # 2. Analyze File Types
    files = session.get("files", [])
    video_files = [f for f in files if f.get('ext', '').lower() in video_extensions]
    doc_files = [f for f in files if f.get('ext', '').lower() not in video_extensions]

    answer = ""
    citations = []
    verified = False
    refusal = False
    llm = LLM()

    # 3. Route the Request via Omni Search
    try:
        if not files:
            answer = "I don't see any files in this session yet. Please upload a PDF, PPT, or Video."
            refusal = True
        else:
            result = llm.ask_question_omni(req.session_id, video_files, doc_files, req.question)
            if isinstance(result, dict):
                answer = result.get("answer", "")
                citations = result.get("citations", [])
                verified = result.get("verified", False)
                refusal = result.get("refusal", False)
            else:
                answer = str(result)

    except Exception as e:
        print(f"Error during QA: {e}")
        if "temporarily unavailable" in str(e) or "503" in str(e) or "429" in str(e):
            answer = "The AI service is temporarily busy. Please try your question again in a moment."
        else:
            answer = "I encountered an error while processing your request."

    # 4. Save Chat History
    assistant_msg = {
        "role": "assistant",
        "text": answer,
        "citations": citations,
        "verified": verified,
        "refusal": refusal,
        "time": datetime.utcnow()
    }
    user_msg = {
        "role": "user",
        "text": req.question,
        "time": datetime.utcnow()
    }

    sessions_col.update_one(
        {"_id": req.session_id},
        {
            "$push": {
                "messages": {
                    "$each": [user_msg, assistant_msg]
                }
            }
        }
    )

    return {
        "answer": answer,
        "citations": citations,
        "verified": verified,
        "refusal": refusal
    }

@app.get("/api/history")
def api_history(session_id: str, current_user=Depends(get_current_user)):
    s = sessions_col.find_one({"_id": session_id, "user_email": current_user["email"]})
    if not s:
        raise HTTPException(403, "Denied")
    return {"session_id": session_id, "messages": s.get("messages", [])}

# ============================================================
# DOCUMENT & VIDEO CONTENT SERVING (ML-4 CITATION GROUNDING)
# ============================================================

def resolve_document_identifiers(doc_uuid: str):
    clean_uuid = os.path.splitext(doc_uuid)[0]

    # Check 1: direct on disk
    file_candidates = [
        os.path.join(UPLOAD_DIR, f"{clean_uuid}.pdf"),
        os.path.join(UPLOAD_DIR, f"{doc_uuid}.pdf"),
        os.path.join(UPLOAD_DIR, doc_uuid),
        os.path.join(UPLOAD_DIR, f"{clean_uuid}.pptx"),
        os.path.join(UPLOAD_DIR, f"{clean_uuid}"),
    ]
    file_path = next((c for c in file_candidates if os.path.exists(c) and not os.path.isdir(c)), None)
    
    json_path = os.path.join("langbase_json", f"{clean_uuid}.json")
    if not os.path.exists(json_path):
        json_path = None

    # Check 2: look up in content_details_col
    if not file_path or not json_path:
        try:
            rec = content_details_col.find_one({"real_name": doc_uuid})
            if not rec:
                rec = content_details_col.find_one({"real_name": f"{clean_uuid}.pdf"})
            if not rec:
                rec = content_details_col.find_one({"real_name": f"{clean_uuid}.pptx"})
            if not rec:
                rec = content_details_col.find_one({"uuid": doc_uuid})
            if not rec:
                rec = content_details_col.find_one({"base_uuid": clean_uuid})
            if not rec:
                for d in content_details_col.find():
                    r_name = d.get("real_name", "").lower()
                    if r_name == doc_uuid.lower() or r_name == f"{clean_uuid}.pdf".lower():
                        rec = d
                        break

            if rec:
                base = rec.get("base_uuid")
                ext = rec.get("content_type", ".pdf")
                if not file_path:
                    for cand in [
                        os.path.join(UPLOAD_DIR, f"{base}{ext}"),
                        os.path.join(UPLOAD_DIR, f"{base}.pdf"),
                        os.path.join(UPLOAD_DIR, f"{base}.pptx"),
                        os.path.join(UPLOAD_DIR, f"{base}"),
                    ]:
                        if os.path.exists(cand) and not os.path.isdir(cand):
                            file_path = cand
                            break
                if not json_path:
                    cand_j = os.path.join("langbase_json", f"{base}.json")
                    if os.path.exists(cand_j):
                        json_path = cand_j
                clean_uuid = base
        except Exception as e:
            print(f"[WARN] Error resolving document identifiers: {e}")

    return file_path, json_path, clean_uuid

@app.get("/api/documents/{doc_uuid}/file")
def get_document_file(doc_uuid: str):
    """Serves the raw PDF/PPTX file for vector canvas rendering in PDF.js"""
    file_path, _, _ = resolve_document_identifiers(doc_uuid)
    if file_path and os.path.exists(file_path):
        media_type = "application/pdf" if file_path.endswith(".pdf") else "application/octet-stream"
        return FileResponse(file_path, media_type=media_type)
    raise HTTPException(404, f"Document file {doc_uuid} not found")

@app.get("/api/documents/{doc_uuid}/metadata")
def get_document_metadata(doc_uuid: str):
    """Returns the parsed layout, tables, text blocks, and bounding boxes"""
    _, json_path, _ = resolve_document_identifiers(doc_uuid)
    if json_path and os.path.exists(json_path):
        with open(json_path, "r", encoding="utf-8") as f:
            return json.load(f)
    raise HTTPException(404, f"Document metadata for {doc_uuid} not found")

@app.get("/api/documents/{doc_uuid}/page/{page_num}/image")
def get_document_page_image(doc_uuid: str, page_num: int):
    """Renders and returns a high-resolution PNG image of the requested PDF page."""
    file_path, _, _ = resolve_document_identifiers(doc_uuid)
    if not file_path or not os.path.exists(file_path):
        raise HTTPException(404, f"Document file {doc_uuid} not found")

    if not file_path.lower().endswith(".pdf"):
        raise HTTPException(400, "Only PDF page images are supported")

    import pymupdf
    try:
        doc = pymupdf.open(file_path)
        if page_num < 1 or page_num > len(doc):
            doc.close()
            raise HTTPException(404, f"Page {page_num} out of range (1-{len(doc)})")

        page = doc.load_page(page_num - 1)
        zoom = 150.0 / 72.0
        mat = pymupdf.Matrix(zoom, zoom)
        pix = page.get_pixmap(matrix=mat, alpha=False)
        img_bytes = pix.tobytes("png")
        doc.close()
        return Response(content=img_bytes, media_type="image/png")
    except Exception as e:
        raise HTTPException(500, f"Error rendering page image: {e}")

@app.get("/api/documents/{doc_uuid}/image/{image_name}")
def get_document_image(doc_uuid: str, image_name: str):
    """Serves extracted chart crops and visual figures"""
    _, _, clean_uuid = resolve_document_identifiers(doc_uuid)
    img_path = os.path.join("langbase_json", "ExtractedImages", clean_uuid, image_name)
    if os.path.exists(img_path):
        return FileResponse(img_path)
    raise HTTPException(404, f"Image {image_name} not found")

def resolve_video_identifiers(video_identifier: str):
    """
    Resolves a video identifier (raw filename, UUID, YouTube URL, or title)
    to its actual downloaded video file on disk and metadata.
    """
    clean_id = video_identifier.strip()
    for ext in video_extensions:
        if clean_id.lower().endswith(ext):
            clean_id = clean_id[:-len(ext)]
            break

    # 1. Check content_details_col for UUID, base_uuid, real_name, or source_url
    det = content_details_col.find_one({
        "$or": [
            {"uuid": video_identifier},
            {"base_uuid": clean_id},
            {"real_name": video_identifier},
            {"source_url": video_identifier},
            {"base_uuid": video_identifier}
        ]
    })

    file_path = None
    source_url = None
    clean_uuid = clean_id

    if det:
        source_url = det.get("source_url")
        base = det.get("base_uuid") or clean_id
        clean_uuid = base
        # Check files under UPLOAD_DIR (downloads/)
        candidates = [
            os.path.join(UPLOAD_DIR, det.get("uuid", "")),
            os.path.join(UPLOAD_DIR, f"{base}{det.get('content_type', '.mp4')}"),
            os.path.join(UPLOAD_DIR, f"{base}.mp4"),
            os.path.join(UPLOAD_DIR, f"{base}.webm"),
            os.path.join(UPLOAD_DIR, f"{base}.mov"),
            os.path.join(UPLOAD_DIR, base)
        ]
        for cand in candidates:
            if cand and os.path.exists(cand) and not os.path.isdir(cand):
                file_path = cand
                break

    # 2. Check direct filename match in UPLOAD_DIR
    if not file_path:
        direct_cands = [
            os.path.join(UPLOAD_DIR, video_identifier),
            os.path.join(UPLOAD_DIR, f"{clean_id}.mp4"),
            os.path.join(UPLOAD_DIR, f"{clean_id}.webm"),
            os.path.join(UPLOAD_DIR, clean_id)
        ]
        for ext in video_extensions:
            direct_cands.append(os.path.join(UPLOAD_DIR, f"{clean_id}{ext}"))

        for cand in direct_cands:
            if os.path.exists(cand) and not os.path.isdir(cand):
                file_path = cand
                break

    return file_path, source_url, clean_uuid

@app.get("/api/videos/{video_identifier:path}/file")
def get_video_file(video_identifier: str):
    """Streams video file for HTML5 video player with timestamp seeking"""
    file_path, _, _ = resolve_video_identifiers(video_identifier)
    if file_path and os.path.exists(file_path):
        media_type = "video/mp4"
        if file_path.endswith(".webm"):
            media_type = "video/webm"
        elif file_path.endswith(".mov"):
            media_type = "video/quicktime"
        return FileResponse(file_path, media_type=media_type)
    raise HTTPException(404, f"Video '{video_identifier}' not found on server")

@app.get("/api/videos/{video_identifier:path}/info")
def get_video_info(video_identifier: str):
    """Returns video metadata and source url if available"""
    file_path, source_url, clean_uuid = resolve_video_identifiers(video_identifier)
    return {
        "video_identifier": video_identifier,
        "clean_uuid": clean_uuid,
        "has_local_file": file_path is not None and os.path.exists(file_path),
        "source_url": source_url,
        "filename": os.path.basename(file_path) if file_path else None
    }


@app.post("/api/upload/link")
def upload_link(req: LinkUpload, current_user=Depends(get_current_user)):
    """Handles external video link / YouTube link upload — full pipeline"""
    session = sessions_col.find_one({"_id": req.session_id, "user_email": current_user["email"]})
    if not session:
        raise HTTPException(403, "Invalid session")

    try:
        # Step 1: Download video
        print(f"[LINK] Downloading video: {req.video_link}", flush=True)
        downloader = VideoDownloader(req.video_link)
        base_id, ext = downloader.yt_download(path=UPLOAD_DIR)
        filename = f"{base_id}{ext}"
        video_path = os.path.join(UPLOAD_DIR, filename)
        print(f"[LINK] Downloaded: {filename}", flush=True)

        # Step 2: Register in content_details
        content_details_col.insert_one({
            "uuid": filename,
            "base_uuid": base_id,
            "real_name": req.video_link,
            "session_id": req.session_id,
            "user_email": current_user["email"],
            "content_type": ext,
            "source_url": req.video_link,
            "uploaded_at": datetime.utcnow()
        })

        # Step 3: Run video pipeline (audio extraction, whisper, YOLO, OCR, Chroma)
        print(f"[LINK] Running video pipeline for {filename}...", flush=True)
        summary = process_video_pipeline(req.session_id, current_user["email"], video_path, ext)
        print(f"[LINK] Pipeline complete. Summary length: {len(summary)}", flush=True)

        return {
            "summary": summary,
            "uuid": base_id,
            "filename": filename,
            "ext": ext
        }

    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(500, f"Video ingestion failed: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    print("[INFO] Starting ExplainX FastAPI Server on http://0.0.0.0:8000 ...")
    uvicorn.run(app, host="0.0.0.0", port=8000)

