from pymongo import MongoClient

MONGO_URI = "mongodb://localhost:27017"

client = MongoClient(MONGO_URI)
db = client["video_explainer"]

users_col = db["users"]
contents_col = db["contents"]
sessions_col = db["sessions"]
doc_registry_col = db["doc_registry_col"]