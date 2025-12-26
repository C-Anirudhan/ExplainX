import os
import json
import numpy as np
import torch
from tqdm import tqdm
from chromadb import PersistentClient
from sentence_transformers import SentenceTransformer


class VectorDB:
    def __init__(self, name):
        """
        name = video name WITHOUT .mp4
        JSON file is expected at: ./langbase_json/{name}.json
        """
        self.name = name
        self.CHROMA_DIR = "./chroma_db"
        self.JSON_PATH = f"langbase_json/{name}.json"
        self.COLLECTION_NAME = "videos"
        self.EMBED_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
        self.BATCH_SIZE = 128

    # ---------------------------------------------------------
    # Embedding model
    # ---------------------------------------------------------
    def get_embedder(self):
        device = "cuda" if torch.cuda.is_available() else "cpu"
        print(f"[INFO] Embedding model on {device}")
        return SentenceTransformer(self.EMBED_MODEL, device=device)

    # ---------------------------------------------------------
    # ChromaDB client
    # ---------------------------------------------------------
    def get_client(self):
        os.makedirs(self.CHROMA_DIR, exist_ok=True)
        return PersistentClient(path=self.CHROMA_DIR)

    # ---------------------------------------------------------
    # INGEST JSON -> ChromaDB
    # ---------------------------------------------------------
    def ingest_json(self):
        print(f"[INFO] Loading JSON: {self.JSON_PATH}")
        if not os.path.exists(self.JSON_PATH):
            print(f"❌ ERROR: JSON not found: {self.JSON_PATH}")
            return

        with open(self.JSON_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)

        video_name = data.get("video_name", "unknown_video")
        frames = data.get("frames", [])
        transcript = data.get("transcript", [])  # ✅ correct key

        print(f"[INFO] Frames found: {len(frames)}")
        print(f"[INFO] Transcript segments: {len(transcript)}")

        documents, metadatas, ids = [], [], []

        # -----------------------------------------------------
        # STORE ALL FRAMES (YOLO + OCR)
        # -----------------------------------------------------
        for fr in frames:

            idx = int(fr.get("frame_index", -1))
            ts = float(fr.get("timestamp", 0.0))

            # YOLO text
            yolo_list = fr.get("yolo_objects", [])
            yolo_text = (
                ", ".join(f"{o['label']}({o['confidence']:.2f})" for o in yolo_list)
                if yolo_list else "None"
            )

            # OCR text
            ocr_list = fr.get("ocr", [])
            ocr_text = (
                " | ".join(o["text"] for o in ocr_list)
                if ocr_list else "None"
            )

            # Final frame text
            doc = (
                f"Frame {idx} at {ts:.2f} sec:\n"
                f"YOLO: {yolo_text}\n"
                f"OCR: {ocr_text}"
            )

            documents.append(doc)
            metadatas.append({
                "video_id": video_name,
                "type": "frame",
                "frame_index": idx,
                "timestamp": ts
            })
            ids.append(f"{video_name}::frame::{idx}")

        # -----------------------------------------------------
        # STORE TRANSCRIPT
        # -----------------------------------------------------
        for i, seg in enumerate(transcript):

            text = seg.get("text", "").strip()
            start = float(seg.get("start", 0.0))
            end = float(seg.get("end", 0.0))

            documents.append(text if text else "(empty)")
            metadatas.append({
                "video_id": video_name,
                "type": "transcript",
                "segment_index": i,
                "start": start,
                "end": end
            })
            ids.append(f"{video_name}::transcript::{i}")

        print(f"[INFO] Total documents to ingest: {len(documents)}")

        # -----------------------------------------------------
        # Chroma Upsert
        # -----------------------------------------------------
        client = self.get_client()

        try:
            col = client.get_collection(self.COLLECTION_NAME)
            print("[INFO] Using existing collection.")
        except:
            col = client.create_collection(self.COLLECTION_NAME)
            print("[INFO] Created new collection.")

        embedder = self.get_embedder()

        for i in tqdm(range(0, len(documents), self.BATCH_SIZE)):
            batch_docs = documents[i:i+self.BATCH_SIZE]
            batch_meta = metadatas[i:i+self.BATCH_SIZE]
            batch_ids = ids[i:i+self.BATCH_SIZE]

            emb = embedder.encode(batch_docs, convert_to_numpy=True)

            col.add(
                ids=batch_ids,
                embeddings=emb.tolist(),
                documents=batch_docs,
                metadatas=batch_meta
            )

        print("\n🔥 INGESTION COMPLETE — ALL DATA STORED!\n")

    # ---------------------------------------------------------
    # SIMPLE QUERY (optional)
    # ---------------------------------------------------------
    def query(self, video_id, question, top_k=5, mode="auto"):
        client = self.get_client()
        col = client.get_collection(self.COLLECTION_NAME)
        embedder = self.get_embedder()

        print(f"[INFO] Querying mode={mode}")

        q_emb = embedder.encode([question], convert_to_numpy=True).tolist()
        q_lower = question.lower()

        # Auto mode logic
        if mode == "auto":
            if "summarize" in q_lower or "summary" in q_lower:
                mode = "transcript"
            else:
                mode = "all"

        # Valid Chroma filters
        if mode == "transcript":
            where = {
                "$and": [
                    {"video_id": {"$eq": video_id}},
                    {"type": {"$eq": "transcript"}}
                ]
            }
        elif mode == "frame":
            where = {
                "$and": [
                    {"video_id": {"$eq": video_id}},
                    {"type": {"$eq": "frame"}}
                ]
            }
        else:
            where = {"video_id": {"$eq": video_id}}

        results = col.query(
            query_embeddings=q_emb,
            n_results=top_k,
            where=where,
            include=["documents", "metadatas", "distances"]
        )

        docs = results.get("documents", [[]])[0]

        print("\n====== RESULTS ======\n")

        if not docs:
            print("❗ No results found.\n")
            return

        metas = results["metadatas"][0]
        dists = results["distances"][0]

        for i in range(len(docs)):
            print(f"[{i+1}] dist={dists[i]:.4f}")
            print(" META:", metas[i])
            print(" DOC:", docs[i][:300], "...\n")
            print("-----------------------------------")
