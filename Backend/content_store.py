from datetime import datetime
from mongo import contents_col

def save_content(user_id: str, content_type: str, source: dict, content: dict):
    doc = {
        "user_id": user_id,
        "type": content_type,   # youtube / website / pdf
        "source": source,
        "content": content,
        "created_at": datetime.utcnow()
    }
    result = contents_col.insert_one(doc)
    return str(result.inserted_id)

def get_content(content_id: str):
    return contents_col.find_one({"_id": content_id})
