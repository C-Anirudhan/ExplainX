import os
import json
import uuid
from threading import Lock
from time import time

# ============================================================
# FILE-BASED SESSION STORE (SAFE VERSION)
# ============================================================

DB_FILE = "session_data.json"
_db_lock = Lock()

# ------------------------------------------------------------
# Ensure DB file exists
# ------------------------------------------------------------
if not os.path.exists(DB_FILE):
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump({}, f)


# ------------------------------------------------------------
# Internal helpers
# ------------------------------------------------------------
def _load_db():
    with _db_lock:
        with open(DB_FILE, "r", encoding="utf-8") as f:
            return json.load(f)


def _save_db(db):
    with _db_lock:
        with open(DB_FILE, "w", encoding="utf-8") as f:
            json.dump(db, f, indent=2)


# ============================================================
# SESSION MANAGEMENT
# ============================================================

def create_session() -> str:
    """
    Create a new chat session and persist it.
    """
    session_id = str(uuid.uuid4())
    db = _load_db()

    db[session_id] = {
        "video_name": None,
        "messages": []
    }

    _save_db(db)
    return session_id


def set_session_video(session_id: str, video_name: str):
    """
    Bind a video to a session.
    Safe even if session does not yet exist.
    """
    db = _load_db()

    if session_id not in db:
        db[session_id] = {
            "video_name": video_name,
            "messages": []
        }
    else:
        db[session_id]["video_name"] = video_name

    _save_db(db)


def get_session_video(session_id: str):
    """
    Get the video associated with a session.
    """
    db = _load_db()
    return db.get(session_id, {}).get("video_name")


# ============================================================
# MESSAGE HANDLING
# ============================================================

def save_message(session_id: str, role: str, content: str):
    """
    Persist a chat message.
    Safe against missing sessions.
    """
    db = _load_db()

    if session_id not in db:
        db[session_id] = {
            "video_name": None,
            "messages": []
        }

    db[session_id]["messages"].append({
        "role": role,
        "content": content,
        "timestamp": int(time() * 1000)  # frontend-friendly
    })

    _save_db(db)


def get_history(session_id: str):
    """
    Retrieve full chat history for a session.
    """
    db = _load_db()
    return db.get(session_id, {}).get("messages", [])


# ============================================================
# OPTIONAL UTILITIES (NOT REQUIRED, BUT USEFUL)
# ============================================================

def session_exists(session_id: str) -> bool:
    db = _load_db()
    return session_id in db


def delete_session(session_id: str):
    db = _load_db()
    if session_id in db:
        del db[session_id]
        _save_db(db)
