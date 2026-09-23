import os
import torch
from chromadb import PersistentClient
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer

CHROMA_DIR = "./chroma_db"
COLLECTION_NAME = "videos"
EMBED_MODEL = "sentence-transformers/all-MiniLM-L6-v2"

_embedder = None
_client = None
_col = None

# ---------------------------------------------------
# Load embedder (Singleton)
# ---------------------------------------------------
def get_embedder():
    global _embedder
    if _embedder is None:
        device = "cuda" if torch.cuda.is_available() else "cpu"
        _embedder = SentenceTransformer(EMBED_MODEL, device=device)
    return _embedder

# ---------------------------------------------------
# Connect to Chroma (Singleton)
# ---------------------------------------------------
def get_client():
    global _client
    if _client is None:
        _client = PersistentClient(
            path=CHROMA_DIR,
            settings=Settings(anonymized_telemetry=False),
        )
    return _client

def get_collection():
    global _col
    if _col is None:
        c = get_client()
        _col = c.get_collection(COLLECTION_NAME)
    return _col

# ---------------------------------------------------
# Convert result list into clean text for LLM
# ---------------------------------------------------
def format_results(results, header):
    out = f"\n\n===== {header} =====\n"
    for r in results:
        out += f"\n• {r['document']}"
    return out

# ---------------------------------------------------
# SAFE, CONTRACT-LOCKED RETRIEVER
# ---------------------------------------------------
def retrieve_combined(video_id: str, question: str, top_k_transcript=10, top_k_frames=10):
    video_id = str(video_id)
    question = str(question)

    col = get_collection()
    embedder = get_embedder()

    q_emb = embedder.encode([question], convert_to_numpy=True).tolist()

    video_variants = list(dict.fromkeys([video_id, os.path.splitext(video_id)[0], f"{os.path.splitext(video_id)[0]}.mp4"]))
    video_filter = {"video_id": {"$in": video_variants}} if len(video_variants) > 1 else {"video_id": {"$eq": video_id}}

    transcript_hits = []
    if top_k_transcript > 0:
        try:
            transcript_results = col.query(
                query_embeddings=q_emb,
                n_results=top_k_transcript,
                where={
                    "$and": [
                        video_filter,
                        {"type": {"$eq": "transcript"}}
                    ]
                },
                include=["documents", "metadatas", "distances"]
            )
            tr_docs = transcript_results.get("documents", [[]])[0]
            tr_meta = transcript_results.get("metadatas", [[]])[0]
            tr_dist = transcript_results.get("distances", [[]])[0]

            transcript_hits = [
                {"document": tr_docs[i], "metadata": tr_meta[i], "distance": tr_dist[i]}
                for i in range(len(tr_docs))
            ]
        except Exception as e:
            print(f"[WARN] Failed to query transcripts: {e}")

    frame_hits = []
    if top_k_frames > 0:
        try:
            frame_results = col.query(
                query_embeddings=q_emb,
                n_results=top_k_frames,
                where={
                    "$and": [
                        video_filter,
                        {"type": {"$eq": "frame"}}
                    ]
                },
                include=["documents", "metadatas", "distances"]
            )
            fr_docs = frame_results.get("documents", [[]])[0]
            fr_meta = frame_results.get("metadatas", [[]])[0]
            fr_dist = frame_results.get("distances", [[]])[0]

            frame_hits = [
                {"document": fr_docs[i], "metadata": fr_meta[i], "distance": fr_dist[i]}
                for i in range(len(fr_docs))
            ]
        except Exception as e:
            print(f"[WARN] Failed to query frames: {e}")

    # ----------------------------- FORMAT
    formatted_transcript = format_results(transcript_hits, "TRANSCRIPT SEGMENTS")
    formatted_frames = format_results(frame_hits, "VISUAL (YOLO + OCR) FRAMES")

    combined_text = (
        "You are analyzing a video.\n"
        "Below are two types of retrieved context:\n"
        "1. Transcript segments (spoken content)\n"
        "2. Frame descriptions (YOLO objects + OCR text)\n\n"
        "Use BOTH to answer the question.\n\n"
        f"{formatted_transcript}\n\n{formatted_frames}"
    )

    return combined_text, transcript_hits, frame_hits
