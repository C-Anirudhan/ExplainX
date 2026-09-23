import os
import json
from datetime import datetime

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
is_mongo_connected = False
client = None
db = None

try:
    from pymongo import MongoClient
    temp_client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=1500)
    # Ping server
    temp_client.admin.command('ping')
    client = temp_client
    db = client["video_explainer"]
    is_mongo_connected = True
    print("[SUCCESS] Connected to MongoDB at", MONGO_URI)
except Exception as e:
    print(f"[INFO] MongoDB not available locally ({e}). Using resilient JSON-backed store.")
    is_mongo_connected = False


if is_mongo_connected and db is not None:
    users_col = db["users"]
    contents_col = db["contents"]
    sessions_col = db["sessions"]
    doc_registry_col = db["doc_registry_col"]
    content_details_col = db["content_details"]
else:
    # Resilient File-backed Collection Simulator
    class ResilientCollection:
        def __init__(self, filename):
            self.file_path = f"local_db_{filename}.json"
            if not os.path.exists(self.file_path):
                with open(self.file_path, "w", encoding="utf-8") as f:
                    json.dump([], f)

        def _read(self):
            try:
                with open(self.file_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                return []

        def _write(self, data):
            # Convert datetimes to ISO string
            def default_serializer(obj):
                if isinstance(obj, datetime):
                    return obj.isoformat()
                return str(obj)

            with open(self.file_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, default=default_serializer)

        def find_one(self, query=None):
            docs = self._read()
            if not query:
                return docs[0] if docs else None

            for d in docs:
                matched = True
                for k, v in query.items():
                    if k == "$or" and isinstance(v, list):
                        or_match = False
                        for sub_q in v:
                            if all(d.get(sk) == sv for sk, sv in sub_q.items()):
                                or_match = True
                                break
                        if not or_match:
                            matched = False
                            break
                    elif d.get(k) != v:
                        matched = False
                        break
                if matched:
                    return d
            return None

        def find(self, query=None):
            docs = self._read()
            if not query:
                results = docs
            else:
                results = []
                for d in docs:
                    matched = True
                    for k, v in query.items():
                        if d.get(k) != v:
                            matched = False
                            break
                    if matched:
                        results.append(d)

            class Cursor:
                def __init__(self, items):
                    self.items = items
                def sort(self, key, direction=1):
                    try:
                        self.items.sort(key=lambda x: x.get(key, 0), reverse=(direction == -1))
                    except Exception:
                        pass
                    return self
                def __iter__(self):
                    return iter(self.items)

            return Cursor(results)

        def insert_one(self, doc):
            docs = self._read()
            docs.append(doc)
            self._write(docs)
            return type("Result", (), {"inserted_id": doc.get("_id")})()

        def update_one(self, query, update):
            docs = self._read()
            for d in docs:
                match = True
                for k, v in query.items():
                    if d.get(k) != v:
                        match = False
                        break
                if match:
                    if "$push" in update:
                        for pk, pv in update["$push"].items():
                            if pk not in d or not isinstance(d[pk], list):
                                d[pk] = []
                            if isinstance(pv, dict) and "$each" in pv:
                                d[pk].extend(pv["$each"])
                            else:
                                d[pk].append(pv)
                    if "$set" in update:
                        for sk, sv in update["$set"].items():
                            d[sk] = sv
                    self._write(docs)
                    return True
            return False

        def delete_many(self, query):
            docs = self._read()
            new_docs = []
            for d in docs:
                match = True
                for k, v in query.items():
                    if isinstance(v, dict) and "$eq" in v:
                        if d.get(k) != v["$eq"]:
                            match = False
                    elif d.get(k) != v:
                        match = False
                if not match:
                    new_docs.append(d)
            self._write(new_docs)

    users_col = ResilientCollection("users")
    contents_col = ResilientCollection("contents")
    sessions_col = ResilientCollection("sessions")
    doc_registry_col = ResilientCollection("doc_registry")
    content_details_col = ResilientCollection("content_details")