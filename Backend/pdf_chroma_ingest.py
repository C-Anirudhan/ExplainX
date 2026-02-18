import os, json, re, uuid
import chromadb
import torch
from PIL import Image
from sentence_transformers import SentenceTransformer
from transformers import CLIPProcessor, CLIPModel

# -----------------------------------------
# Hierarchical Smart Chunking
# -----------------------------------------

def split_paragraphs(text):
    return [p.strip() for p in re.split(r"\n{2,}", text) if len(p.strip()) > 40]

def sentence_chunks(text):
    return re.split(r"(?<=[.!?])\s+", text)

def sliding_chunks(tokens, size=420, overlap=120):
    i = 0
    while i < len(tokens):
        yield tokens[i:i+size]
        i += size - overlap

# -----------------------------------------
# Chat-Scoped Multimodal Chroma DB
# -----------------------------------------

class ChromaMultimodalDB:
    def __init__(self, chat_id, doc_uuid=None):
        self.data = {}
        self.chat_id = chat_id
        self.doc_uuid = doc_uuid
        self.collection_name = f"chat_{chat_id}"

        # 🔥 CHANGED: Use PersistentClient to save to local disk
        self.client = chromadb.PersistentClient(path="./chroma_db_storage")
        
        self.collection = self.client.get_or_create_collection(self.collection_name)

        self.text_model = SentenceTransformer("sentence-transformers/all-mpnet-base-v2")
        self.clip_model = CLIPModel.from_pretrained("openai/clip-vit-base-patch32")
        self.clip_processor = CLIPProcessor.from_pretrained("openai/clip-vit-base-patch32")

        if self.doc_uuid:
            self.json_path = f"langbase_json/{self.doc_uuid}.json"
            self.image_dir = f"langbase_json/ExtractedImages/{self.doc_uuid}/"
            # Check if file exists before opening to prevent errors
            if os.path.exists(self.json_path):
                with open(self.json_path, "r", encoding="utf-8") as f:
                    self.data = json.load(f)

    # -----------------------------------------
    # TEXT INGEST
    # -----------------------------------------
    def ingest_text(self):
        for page, content in self.data.items():
            raw_text = content.get("text", "")
            images = content.get("images", [])

            for p_id, para in enumerate(split_paragraphs(raw_text)):
                tokens = " ".join(sentence_chunks(para)).split()

                for w_id, token_chunk in enumerate(sliding_chunks(tokens)):
                    chunk_text = " ".join(token_chunk)
                    emb = self.text_model.encode(chunk_text).tolist()

                    cid = f"{self.chat_id}_{uuid.uuid4()}"

                    self.collection.add(
                        ids=[cid],
                        documents=[chunk_text],
                        embeddings=[emb],
                        metadatas=[{
                            "chat_id": self.chat_id,
                            "doc_uuid": self.doc_uuid,
                            "page": page,
                            "paragraph": p_id,
                            "window": w_id,
                            "images": ",".join(images),
                            "type": "text"
                        }]
                    )
        print("✅ Hierarchical chat-brain chunks ingested")

    # -----------------------------------------
    # IMAGE INGEST
    # -----------------------------------------
    def ingest_images(self):
        if not os.path.exists(self.image_dir):
            print(f"Image directory not found: {self.image_dir}")
            return

        for fname in os.listdir(self.image_dir):
            path = os.path.join(self.image_dir, fname)
            image_id,_ = os.path.splitext(fname)

            try:
                img = Image.open(path).convert("RGB")
                inputs = self.clip_processor(images=img, return_tensors="pt")

                with torch.no_grad():
                    emb = self.clip_model.get_image_features(**inputs)[0].tolist()

                self.collection.add(
                    ids=[f"{self.chat_id}_{self.doc_uuid}_img_{image_id}"],
                    embeddings=[emb],
                    metadatas=[{
                        "chat_id": self.chat_id,
                        "doc_uuid": self.doc_uuid,
                        "type": "image",
                        "image_id": image_id
                    }]
                )
            except Exception as e:
                print(f"Skipping image {fname}: {e}")

        print("✅ Chat-brain image embeddings ingested")

    def ingest_all(self):
        self.ingest_text()
        self.ingest_images()
        print("🚀 Full multimodal chat-brain ingestion complete")

    # -----------------------------------------
    # CHAT-SCOPED QUERY (BUG-2 FIXED)
    # -----------------------------------------
    def query_text(self, query, top_k=10):
        q_emb = self.text_model.encode(query).tolist()
        res = self.collection.query(
            query_embeddings=[q_emb],
            n_results=top_k,
            where={"chat_id": {"$eq": self.chat_id}}
        )
        return res["documents"][0] if res["documents"] else []

    def query_grouped(self, question, top_k=25, only_doc=None):
        q_emb = self.text_model.encode(question).tolist()

        # If active_doc exists, search ONLY inside that doc
        where_filter = {"chat_id": {"$eq": self.chat_id}}

        if only_doc:
            where_filter = {
                "$and": [
                    {"chat_id": {"$eq": self.chat_id}},
                    {"doc_uuid": {"$eq": only_doc}}
                ]
            }

        res = self.collection.query(
            query_embeddings=[q_emb],
            n_results=top_k,
            where=where_filter,
            include=["documents","metadatas"]
        )

        grouped = {}
        if res["documents"]:
            for doc, meta in zip(res["documents"][0], res["metadatas"][0]):
                doc_id = meta.get("doc_uuid", "unknown")
                grouped.setdefault(doc_id, []).append(doc)

        return grouped