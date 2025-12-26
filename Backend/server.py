from fastapi import FastAPI, UploadFile, File, Form, Depends, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uuid
import os
import shutil
from sqlalchemy.orm import Session

# ======== DATABASE SETUP ========
from database import SessionLocal, engine, Base
from models import User
from auth_utils import (
    hash_password,
    verify_password,
    create_access_token,
    decode_token,
)

# ======== VIDEO PROCESSING MODULES ========
from download_video import VideoDownloader
from detect_video_audio import gen_json
from ingest_and_query_chroma import VectorDB
from ExplainX_LLM import LLM

# ======== SESSION STATE HANDLING ========
from session_state import (
    create_session,
    set_session_video,
    get_session_video,
    save_message,
    get_history,
)

# Create DB tables
Base.metadata.create_all(bind=engine)

# Init FastAPI
app = FastAPI()

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

UPLOAD_DIR = "downloads/"
os.makedirs(UPLOAD_DIR, exist_ok=True)


# ============================================================
# DB DEPENDENCY
# ============================================================

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


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


# ============================================================
# SIGNUP ROUTE
# ============================================================

@app.post("/api/signup")
def signup(req: SignupRequest, db: Session = Depends(get_db)):
    user_exists = db.query(User).filter(User.email == req.email).first()
    if user_exists:
        raise HTTPException(status_code=400, detail="Email already registered")

    new_user = User(
        name=req.username,
        email=req.email,
        password_hash=hash_password(req.password),
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return {"message": "User created successfully"}


# ============================================================
# LOGIN ROUTE
# ============================================================

@app.post("/api/login")
def login(req: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == req.email).first()
    if not user or not verify_password(req.password, user.password_hash):
        raise HTTPException(status_code=400, detail="Invalid credentials")

    token = create_access_token({"sub": user.email})

    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {"name": user.name, "email": user.email},
    }


# ============================================================
# AUTH MIDDLEWARE (JWT)
# ============================================================

def get_current_user(
    authorization: str = Header(None), db: Session = Depends(get_db)
):
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing Authorization header")

    try:
        scheme, token = authorization.split()
        if scheme.lower() != "bearer":
            raise Exception()
    except:
        raise HTTPException(status_code=401, detail="Invalid Authorization format")

    try:
        payload = decode_token(token)
        email = payload.get("sub")
    except:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    return user


@app.post("/api/me")
def me(current_user: User = Depends(get_current_user)):
    return {"name": current_user.name, "email": current_user.email}


# ============================================================
# VIDEO PIPELINE
# ============================================================

class LinkUpload(BaseModel):
    session_id: str
    video_link: str


class AskRequest(BaseModel):
    session_id: str
    question: str


def process_video_pipeline(session_id: str, input_path: str):
    filename = os.path.basename(input_path)

    processor = gen_json(filename)
    output = processor.main()
    if not output:
        raise HTTPException(status_code=500, detail="Video processing failed")

    vectordb = VectorDB(filename)
    vectordb.ingest_json()

    initial_summary = LLM().summarize_video(filename)

    set_session_video(session_id, filename)
    save_message(session_id, "assistant", initial_summary)

    return initial_summary



# ============================================================
# CREATE NEW SESSION
# ============================================================

@app.post("/api/new-session")
def api_new_session():
    session_id = create_session()
    return {"session_id": session_id}


# ============================================================
# UPLOAD BY LINK
# ============================================================

@app.post("/api/upload/link")
def upload_link(req: LinkUpload):
    session_id = req.session_id
    video_link = req.video_link

    file_path = VideoDownloader(video_link).yt_download()
    if not file_path:
        return {"error": "Video download failed"}
    filename = os.path.basename(file_path)
    summary = process_video_pipeline(session_id, file_path)

    return {
    "status": "processed",
    "source": "link",
    "video_file": filename,
    "summary": summary,
}



# ============================================================
# UPLOAD FILE (.mp4 only for now)
# ============================================================

@app.post("/api/upload/file")
def upload_file(session_id: str = Form(...), file: UploadFile = File(...)):
    ext = file.filename.split(".")[-1].lower()

    saved_path = os.path.join(UPLOAD_DIR, f"{uuid.uuid4()}.{ext}")
    with open(saved_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    if ext in ["mp4", "mkv", "mov"]:
        summary = process_video_pipeline(session_id, saved_path)
        filename = os.path.basename(saved_path)
        return {
            "status": "processed",
            "source": "file",
            "video_file": filename,
            "summary": summary,
        }

    return {"error": f"File type '{ext}' not supported yet"}


# ============================================================
# ASK QUESTION (LLM + RAG)
# ============================================================

@app.post("/api/ask")
def api_ask(req: AskRequest):
    session_id = req.session_id
    question = req.question
    processed_path = get_session_video(session_id)

    

    if not processed_path:
        raise HTTPException(
            status_code=400,
            detail="No video associated with this session"
        )
    filename = os.path.basename(processed_path)
    print(filename, question)

    
    try:
        answer = LLM().ask_question(filename, question)
    except:
        answer = "Error processing the question. Please try again later."

    save_message(session_id, "user", question)
    save_message(session_id, "assistant", answer)

    if not answer:
        return "The model could not generate an answer for this question."

    return {"answer": answer}


# ============================================================
# GET SESSION HISTORY
# ============================================================

@app.get("/api/history")
def api_history(session_id: str):
    return {"session_id": session_id, "messages": get_history(session_id)}