from datetime import datetime
from mongo import doc_registry_col

def register_document(chat_id, doc_uuid, filename):
    doc_registry_col.update_one(
        {"_id": chat_id},
        {
            "$set": {
                f"docs.{doc_uuid}": {
                    "filename": filename,
                    "uploaded_at": datetime.utcnow().isoformat()
                }
            }
        },
        upsert=True
    )

def resolve_filename(chat_id, doc_uuid):
    doc = doc_registry_col.find_one({"_id": chat_id}, {"docs": 1})
    if not doc:
        return None
    return doc["docs"].get(doc_uuid, {}).get("filename")

def list_documents(chat_id):
    doc = doc_registry_col.find_one({"_id": chat_id}, {"docs": 1})
    if not doc:
        return {}
    return doc["docs"]

def delete_document(chat_id, doc_uuid):
    doc_registry_col.update_one(
        {"_id": chat_id},
        {"$unset": {f"docs.{doc_uuid}": ""}}
    )
