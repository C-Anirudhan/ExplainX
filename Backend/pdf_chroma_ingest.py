import os
import json
import re
import uuid
import chromadb
from chromadb.config import Settings
import torch
from sentence_transformers import SentenceTransformer

# -----------------------------------------
# Helpers
# -----------------------------------------

def split_paragraphs(text):
    return [p.strip() for p in re.split(r"\n{2,}", text) if len(p.strip()) > 30]

def sliding_chunks(tokens, size=350, overlap=80):
    i = 0
    while i < len(tokens):
        yield tokens[i:i+size]
        i += size - overlap


# -----------------------------------------
# Chat-Scoped Multimodal Chroma DB
# -----------------------------------------

class ChromaMultimodalDB:
    # Class-level model cache to avoid re-loading on every instantiation
    _text_model = None

    @classmethod
    def get_text_model(cls):
        if cls._text_model is None:
            device = "cuda" if torch.cuda.is_available() else "cpu"
            print(f"[INFO] Initializing embedding model on {device} (all-MiniLM-L6-v2)")
            try:
                cls._text_model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2", device=device, local_files_only=True)
            except Exception:
                cls._text_model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2", device=device)
        return cls._text_model

    def __init__(self, chat_id, doc_uuid=None):
        self.data = {}
        self.chat_id = str(chat_id)
        self.doc_uuid = str(doc_uuid) if doc_uuid else None
        self.collection_name = f"chat_{self.chat_id}"

        chroma_storage_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "chroma_db_storage")
        self.client = chromadb.PersistentClient(
            path=chroma_storage_dir,
            settings=Settings(anonymized_telemetry=False),
        )
        self.collection = self.client.get_or_create_collection(self.collection_name)
        self.text_model = self.get_text_model()

        if self.doc_uuid:
            self.json_path = f"langbase_json/{self.doc_uuid}.json"
            if os.path.exists(self.json_path):
                try:
                    with open(self.json_path, "r", encoding="utf-8") as f:
                        self.data = json.load(f)
                except Exception as e:
                    print(f"[WARN] Error reading {self.json_path}: {e}")

    # -----------------------------------------
    # RICH MIXED-FORMAT TEXT & TABLE INGEST
    # -----------------------------------------
    def ingest_text(self):
        if not self.data:
            print(f"[WARN] No data to ingest for doc_uuid={self.doc_uuid}")
            return

        documents = []
        metadatas = []
        ids = []

        for page_key, content in self.data.items():
            page_num = content.get("page_num", 1)
            try:
                # If page_key is like "page_3", extract integer if page_num missing
                if "page_" in page_key and page_num == 1:
                    page_num = int(page_key.split("_")[1])
            except Exception:
                pass

            tables = content.get("tables", [])
            text_blocks = content.get("text_blocks", [])
            images = content.get("images", [])

            # 1. Ingest Tables (Higher semantic priority)
            for t_idx, table in enumerate(tables, start=1):
                t_md = table.get("markdown", "")
                t_bbox = table.get("bbox", [0, 0, 0, 0])
                t_id = table.get("table_id", f"p{page_num}_t{t_idx}")
                
                doc_text = f"Document: {self.doc_uuid} | Page {page_num} Table ({t_id}):\n{t_md}"
                cid = f"{self.chat_id}_{self.doc_uuid}_{t_id}_{uuid.uuid4().hex[:6]}"
                
                documents.append(doc_text)
                metadatas.append({
                    "chat_id": self.chat_id,
                    "doc_uuid": self.doc_uuid or "unknown",
                    "page": int(page_num),
                    "bbox": json.dumps(t_bbox),
                    "chunk_type": "table",
                    "element_id": t_id,
                    "label": f"Page {page_num} Table {t_idx}",
                    "raw_text": t_md
                })
                ids.append(cid)

            # 2. Ingest Text Blocks with Spatial Coordinates
            if text_blocks:
                for b_idx, block in enumerate(text_blocks, start=1):
                    b_text = block.get("text", "").strip()
                    if len(b_text) < 15:
                        continue
                    b_bbox = block.get("bbox", [0, 0, 0, 0])
                    b_id = block.get("block_id", f"p{page_num}_b{b_idx}")

                    b_lower = b_text.lower()
                    if "bonafide" in b_lower or "certif" in b_lower:
                        sec_label = f"Page {page_num} Bonafide Certification"
                    elif "purpose" in b_lower or "loan" in b_lower:
                        sec_label = f"Page {page_num} Purpose"
                    elif "trust" in b_lower or "signatory" in b_lower:
                        sec_label = f"Page {page_num} Trust & Signatory"
                    elif "overview" in b_lower or "growth" in b_lower or "margin" in b_lower:
                        sec_label = f"Page {page_num} Financial Overview"
                    else:
                        sec_label = f"Page {page_num} Section {b_idx}"

                    doc_text = f"Document: {self.doc_uuid} | {sec_label}:\n{b_text}"
                    cid = f"{self.chat_id}_{self.doc_uuid}_{b_id}_{uuid.uuid4().hex[:6]}"

                    documents.append(doc_text)
                    metadatas.append({
                        "chat_id": self.chat_id,
                        "doc_uuid": self.doc_uuid or "unknown",
                        "page": int(page_num),
                        "bbox": json.dumps(b_bbox),
                        "chunk_type": "text",
                        "element_id": b_id,
                        "label": sec_label,
                        "raw_text": b_text
                    })
                    ids.append(cid)
            else:
                # Fallback for legacy unstructured JSON without text_blocks
                raw_text = content.get("text", "")
                for p_id, para in enumerate(split_paragraphs(raw_text)):
                    tokens = para.split()
                    for w_id, token_chunk in enumerate(sliding_chunks(tokens)):
                        chunk_text = " ".join(token_chunk)
                        cid = f"{self.chat_id}_{self.doc_uuid}_p{page_num}_para{p_id}_w{w_id}_{uuid.uuid4().hex[:6]}"
                        documents.append(chunk_text)
                        metadatas.append({
                            "chat_id": self.chat_id,
                            "doc_uuid": self.doc_uuid or "unknown",
                            "page": int(page_num),
                            "bbox": json.dumps([0, 0, 0, 0]),
                            "chunk_type": "text",
                            "element_id": f"p{page_num}_para{p_id}",
                            "label": f"Page {page_num}",
                            "raw_text": chunk_text
                        })
                        ids.append(cid)

            # 3. Ingest Visual Elements (Charts & Figures)
            for im_idx, img in enumerate(images, start=1):
                img_bbox = img.get("bbox", [0, 0, 0, 0]) if isinstance(img, dict) else [0, 0, 0, 0]
                img_name = img.get("filename", str(img)) if isinstance(img, dict) else str(img)
                is_chart = img.get("is_chart", False) if isinstance(img, dict) else False

                chunk_desc = f"Document: {self.doc_uuid} | Page {page_num} {'Chart/Graphic' if is_chart else 'Image'}: {img_name}"
                cid = f"{self.chat_id}_{self.doc_uuid}_p{page_num}_img{im_idx}_{uuid.uuid4().hex[:6]}"

                documents.append(chunk_desc)
                metadatas.append({
                    "chat_id": self.chat_id,
                    "doc_uuid": self.doc_uuid or "unknown",
                    "page": int(page_num),
                    "bbox": json.dumps(img_bbox),
                    "chunk_type": "chart" if is_chart else "image",
                    "element_id": f"p{page_num}_img{im_idx}",
                    "label": f"Page {page_num} {'Chart' if is_chart else 'Figure'}",
                    "raw_text": chunk_desc
                })
                ids.append(cid)

        # Batch embed and write to Chroma
        if documents:
            batch_size = 64
            for i in range(0, len(documents), batch_size):
                b_docs = documents[i:i+batch_size]
                b_meta = metadatas[i:i+batch_size]
                b_ids = ids[i:i+batch_size]
                b_embs = self.text_model.encode(b_docs, convert_to_numpy=True).tolist()

                self.collection.add(
                    ids=b_ids,
                    documents=b_docs,
                    embeddings=b_embs,
                    metadatas=b_meta
                )

            print(f"[SUCCESS] Ingested {len(documents)} spatial chunks (tables, text, visuals) for {self.doc_uuid}")

    def ingest_all(self):
        self.ingest_text()

    # -----------------------------------------
    # RETRIEVAL (PRESERVING RICH METADATA)
    # -----------------------------------------
    def query_text(self, query, top_k=10):
        """Simple text query returning raw document strings for backward compatibility."""
        q_emb = self.text_model.encode([query], convert_to_numpy=True).tolist()
        result_count = self.collection.count()
        if result_count == 0:
            return []

        res = self.collection.query(
            query_embeddings=q_emb,
            n_results=min(top_k, result_count),
            where={"chat_id": {"$eq": self.chat_id}}
        )
        return res["documents"][0] if res["documents"] else []

    def query_grouped(self, question, top_k=25, only_doc=None):
        """
        Retrieves top_k chunks and groups them by document UUID.
        Returns rich structured hit objects with bounding boxes, pages, and chunk types.
        """
        result_count = self.collection.count()
        if result_count == 0:
            return {}

        q_emb = self.text_model.encode([question], convert_to_numpy=True).tolist()

        where_filter = {"chat_id": {"$eq": self.chat_id}}
        if only_doc:
            where_filter = {
                "$and": [
                    {"chat_id": {"$eq": self.chat_id}},
                    {"doc_uuid": {"$eq": only_doc}}
                ]
            }

        res = self.collection.query(
            query_embeddings=q_emb,
            n_results=min(top_k, result_count),
            where=where_filter,
            include=["documents", "metadatas", "distances"]
        )

        grouped = {}
        if res["documents"] and res["documents"][0]:
            docs = res["documents"][0]
            metas = res["metadatas"][0]
            dists = res["distances"][0]

            for doc, meta, dist in zip(docs, metas, dists):
                doc_id = meta.get("doc_uuid", "unknown")
                bbox = meta.get("bbox", "[0,0,0,0]")
                if isinstance(bbox, str):
                    try:
                        bbox = json.loads(bbox)
                    except Exception:
                        bbox = [0, 0, 0, 0]

                chunk_obj = {
                    "document": doc,
                    "raw_text": meta.get("raw_text", doc),
                    "page": int(meta.get("page", 1)),
                    "bbox": bbox,
                    "chunk_type": meta.get("chunk_type", "text"),
                    "element_id": meta.get("element_id", ""),
                    "label": meta.get("label", f"Page {meta.get('page', 1)}"),
                    "doc_uuid": doc_id,
                    "distance": float(dist)
                }

                grouped.setdefault(doc_id, []).append(chunk_obj)

        return grouped
