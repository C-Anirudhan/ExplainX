from fastapi import FastAPI, UploadFile, File, Form, Depends, HTTPException, Header, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uuid, os, shutil
from datetime import datetime
from process_ppt import Ppt2Pdf

# ======== PDF / VIDEO / RAG ========
from pdf_ppt_extract import Pdf2Json
from pdf_chroma_ingest import ChromaMultimodalDB
from download_video import VideoDownloader
from detect_video_audio import gen_json
from ingest_and_query_chroma import VectorDB
from ExplainX_LLM import LLM
from web_scrapper import FullPageExtractor

# ======== MONGODB ========
from mongo import users_col, sessions_col

# ======== AUTH UTILS ========
from auth_utils import (
    hash_password,
    verify_password,
    create_access_token,
    decode_token,
)

# ============================================================
# FASTAPI INIT
# ============================================================

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================================
# CONSTANTS
# ============================================================

UPLOAD_DIR = "downloads/"
os.makedirs(UPLOAD_DIR, exist_ok=True)

video_extensions = {
    ".mp4", ".m4v", ".mov", ".avi", ".mkv", ".webm", ".flv", ".wmv",
    ".mpg", ".mpeg", ".3gp", ".3g2", ".ts", ".mts", ".m2ts", ".vob",
    ".ogv", ".f4v", ".rm", ".rmvb", ".asf", ".divx", ".xvid", ".dv",
    ".amv", ".yuv"
}

# ============================================================
# AUTH SCHEMAS
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

# ============================================================
# AUTH DEPENDENCY (OPTIONS SAFE)
# ============================================================

def get_current_user(
    request: Request,
    authorization: str = Header(None)
):
    if request.method == "OPTIONS":
        return None

    if not authorization:
        raise HTTPException(status_code=401, detail="Missing Authorization header")

    try:
        scheme, token = authorization.split()
        if scheme.lower() != "bearer":
            raise Exception()
        payload = decode_token(token)
        email = payload.get("sub")
    except:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    user = users_col.find_one({"email": email})
    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    return user

# ============================================================
# AUTH ROUTES
# ============================================================

@app.post("/api/signup")
def signup(req: SignupRequest):
    if users_col.find_one({"email": req.email}):
        raise HTTPException(status_code=400, detail="Email already registered")

    users_col.insert_one({
        "email": req.email,
        "username": req.username,
        "password_hash": hash_password(req.password),
        "created_at": datetime.utcnow()
    })

    return {"message": "User created successfully"}

@app.post("/api/login")
def login(req: LoginRequest):
    user = users_col.find_one({"email": req.email})
    if not user or not verify_password(req.password, user["password_hash"]):
        raise HTTPException(status_code=400, detail="Invalid credentials")

    token = create_access_token({"sub": user["email"]})

    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "name": user["username"],
            "email": user["email"]
        },
    }

@app.post("/api/me")
def api_me(current_user=Depends(get_current_user)):
    return {
        "name": current_user["username"],
        "email": current_user["email"]
    }

# ============================================================
# SESSIONS
# ============================================================

@app.post("/api/new-session")
def api_new_session(current_user=Depends(get_current_user)):
    session_id = str(uuid.uuid4())

    sessions_col.insert_one({
        "_id": session_id,
        "user_email": current_user["email"],
        "video_file": None,
        "messages": [],
        "created_at": datetime.utcnow()
    })

    return {"session_id": session_id}

# ============================================================
# 🟢 SIDEBAR HISTORY (THIS FIXES YOUR ISSUE)
# ============================================================

@app.get("/api/sessions")
def api_sessions(current_user=Depends(get_current_user)):
    sessions = sessions_col.find(
        {"user_email": current_user["email"]}
    ).sort("created_at", -1)

    result = []

    for s in sessions:
        messages = s.get("messages", [])

        title = "New Conversation"
        for m in messages:
            if m.get("role") == "user":
                title = m.get("text", "")[:40]
                break

        result.append({
            "id": s["_id"],                      # ✔ sidebar expects this
            "title": title,                      # ✔ sidebar expects this
            "timestamp": s.get("created_at"),    # ✔ sidebar expects this
            "files": [s["video_file"]] if s.get("video_file") else []
        })

    return result

# ============================================================
# VIDEO / PDF PIPELINE
# ============================================================

def process_video_pipeline(session_id: str, user_email: str, input_path: str,ext):
    filename = os.path.basename(input_path)

    gen_json(filename).main()
    VectorDB(filename).ingest_json()

    summary = LLM().summarize_video(filename)

    sessions_col.update_one(
        {"_id": session_id, "user_email": user_email},
        {"$set": {"video_file": filename, "ext": ext},
         "$push": {"messages": {
             "role": "assistant",
             "text": summary,
             "time": datetime.utcnow()
         }}}
    )

    return summary

def process_pdf_ppt_pipeline(session_id: str, user_email: str, input_path: str,ext):
    filename = os.path.basename(input_path)

    Pdf2Json(filename).extract()
    ChromaMultimodalDB(filename).ingest_text()

    summary = LLM().summarize_pdf(filename)

    sessions_col.update_one(
        {"_id": session_id, "user_email": user_email},
        {"$set": {"video_file": filename,"ext":ext},
         "$push": {"messages": {
             "role": "assistant",
             "text": summary,
             "time": datetime.utcnow()
         }}}
    )

    return summary

# ============================================================
# UPLOAD ROUTES
# ============================================================

@app.post("/api/upload/link")
def upload_link(req: LinkUpload, current_user=Depends(get_current_user)):
    session = sessions_col.find_one({
        "_id": req.session_id,
        "user_email": current_user["email"]
    })

    if not session:
        raise HTTPException(status_code=403, detail="Invalid session")
    link =req.video_link
    ans=""
    for i in link.split('/'):
        ans += i.replace('.','')
        ans += ' '
    if 'youtube' in ans.lower().split():
        file_path,ext = VideoDownloader(link).yt_download()
        print(file_path, ext)
        file_path = f"{file_path}{ext}"
        summary = process_video_pipeline(req.session_id, current_user["email"], file_path, ext)
        return {"status": "processed", "summary": summary}
    else:
        web = FullPageExtractor(link)
        filename,result = web.extract() 
        summary = result["content"]["full_text"]
        return {"status": "processed", "summary": summary}

@app.post("/api/upload/file")
def upload_file(
    session_id: str = Form(...),
    file: UploadFile = File(...),
    current_user=Depends(get_current_user)
):
    session = sessions_col.find_one({
        "_id": session_id,
        "user_email": current_user["email"]
    })

    if not session:
        raise HTTPException(status_code=403, detail="Invalid session")

    ext = os.path.splitext(file.filename)[1].lower()
    saved_path = os.path.join(UPLOAD_DIR, f"{uuid.uuid4()}{ext}")

    with open(saved_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    if ext in video_extensions:
        return {"summary": process_video_pipeline(session_id, current_user["email"], saved_path,ext)}
    elif ext == ".pdf":
        return {"summary": process_pdf_ppt_pipeline(session_id, current_user["email"], saved_path[:-4],ext)}
    elif ext == ".ppt" or ext == ".pptx":
        Ppt2Pdf(saved_path[:-len(ext)],ext[1:]).convert_ppt_to_pdf()
        return {"summary": process_pdf_ppt_pipeline(session_id, current_user["email"], saved_path[:-len(ext)],ext)}
    else:
        raise HTTPException(status_code=400, detail="Unsupported file type")

# ============================================================
# ASK + HISTORY
# ============================================================

@app.post("/api/ask")
def api_ask(req: AskRequest, current_user=Depends(get_current_user)):
    session = sessions_col.find_one({
        "_id": req.session_id,
        "user_email": current_user["email"]
    })

    if not session:
        raise HTTPException(status_code=403, detail="Invalid session")

    if not session.get("video_file"):
        raise HTTPException(status_code=400, detail="No file attached")

    if session["ext"] in video_extensions:
        answer = LLM().ask_question(session["video_file"], req.question)
        sessions_col.update_one(
            {"_id": req.session_id},
            {"$push": {"messages": [
                {"role": "user", "text": req.question, "time": datetime.utcnow()},
                {"role": "assistant", "text": answer, "time": datetime.utcnow()}
            ]}}
        )   

        return {"answer": answer}
    elif session["ext"] in ['.pdf','.ppt','.pptx']:
        answer = LLM().ask_question_ppt_pdf(session["video_file"], req.question)
        sessions_col.update_one(
            {"_id": req.session_id},
            {"$push": {"messages": [
                {"role": "user", "text": req.question, "time": datetime.utcnow()},
                {"role": "assistant", "text": answer, "time": datetime.utcnow()}
            ]}}
        )
        return {"answer": answer}
    return {"answer": None}

@app.get("/api/history")
def api_history(session_id: str, current_user=Depends(get_current_user)):
    session = sessions_col.find_one({
        #"_id": session_id,
        "user_email": current_user["email"]
    })

    if not session:
        raise HTTPException(status_code=403, detail="Access denied")

    return {
        "session_id": session_id,
        "messages": session.get("messages", [])
    }
