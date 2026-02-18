import os
os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"
os.environ["TRANSFORMERS_FORCE_SAFE_LOADING"] = "1"
os.environ["HF_HUB_DISABLE_TELEMETRY"] = "1"
os.environ["HF_HUB_ENABLE_HF_TRANSFER"] = "0"

from fastapi import FastAPI, UploadFile, File, Form, Depends, HTTPException, Header, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uuid, shutil
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

from mongo import users_col, sessions_col
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
        raise HTTPException(401, "Missing Authorization")
    try:
        scheme, token = authorization.split()
        payload = decode_token(token)
        email = payload["sub"]
    except:
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

        res.append({
            "id": s["_id"], 
            "title": title, 
            "timestamp": s["created_at"], 
            "files": s.get("files", [])
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
    path = os.path.join(UPLOAD_DIR,f"{uuid.uuid4()}{ext}")
    
    with open(path,"wb") as f: shutil.copyfileobj(file.file,f)

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

    return {"summary": summary}

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
    video_files = [f for f in files if f['ext'] in video_extensions]
    doc_files = [f for f in files if f['ext'] not in video_extensions]

    answer = ""
    llm = LLM()

    # 3. Route the Request (Video vs PDF vs Hybrid)
    try:
        if video_files and not doc_files:
            # SCENARIO A: Only Videos
            target_video = video_files[-1]["name"] 
            print(f"Routing to Video DB for: {target_video}")
            # Ensure LLM class has ask_question_video method!
            answer = llm.ask_question(target_video, req.question)

        elif doc_files and not video_files:
            # SCENARIO B: Only Docs
            print("Routing to PDF/PPT DB")
            answer = llm.ask_question_ppt_pdf(req.session_id, req.question)

        elif video_files and doc_files:
            # SCENARIO C: Hybrid (Prioritize most recent upload)
            last_file = files[-1]
            if last_file['ext'] in video_extensions:
                 answer = llm.ask_question(last_file["name"], req.question)
            else:
                 answer = llm.ask_question_ppt_pdf(req.session_id, req.question)
        else:
            answer = "I don't see any files in this session yet. Please upload a PDF, PPT, or Video."

    except Exception as e:
        print(f"Error during QA: {e}")
        answer = "I encountered an error while processing your request."

    # 4. Save Chat History (FIXED: Using $each to prevent nested arrays)
    sessions_col.update_one(
        {"_id": req.session_id},
        {
            "$push": {
                "messages": {
                    "$each": [
                        {"role": "user", "text": req.question, "time": datetime.utcnow()},
                        {"role": "assistant", "text": answer, "time": datetime.utcnow()}
                    ]
                }
            }
        }
    )

    return {"answer": answer}

@app.get("/api/history")
def api_history(session_id:str, current_user=Depends(get_current_user)):
    s = sessions_col.find_one({"_id":session_id,"user_email":current_user["email"]})
    if not s: raise HTTPException(403,"Denied")
    return {"session_id":session_id,"messages":s.get("messages",[])}