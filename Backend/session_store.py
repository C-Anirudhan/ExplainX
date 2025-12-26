from uuid import uuid4
from datetime import datetime
from mongo import sessions_col

# ---------------- CREATE SESSION ----------------
def create_session(user_id: str, content_id: str):
    session = {
        "_id": str(uuid4()),
        "user_id": user_id,
        "content_id": content_id,
        "messages": [],
        "created_at": datetime.utcnow()
    }
    sessions_col.insert_one(session)
    return session["_id"]

# ---------------- VERIFY SESSION ----------------
def get_session(session_id: str, user_id: str, content_id: str):
    session = sessions_col.find_one({
        "_id": session_id,
        "user_id": user_id,
        "content_id": content_id
    })

    if not session:
        raise Exception("Session conflict or invalid session")

    return session

# ---------------- SAVE MESSAGE ----------------
def save_message(session_id: str, role: str, text: str):
    sessions_col.update_one(
        {"_id": session_id},
        {"$push": {
            "messages": {
                "role": role,
                "text": text,
                "timestamp": datetime.utcnow()
            }
        }}
    )

# ---------------- FETCH HISTORY ----------------
def get_chat_history(session_id: str):
    session = sessions_col.find_one(
        {"_id": session_id},
        {"messages": 1, "_id": 0}
    )
    return session["messages"] if session else []
