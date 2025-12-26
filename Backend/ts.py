import chromadb
from chromadb import PersistentClient
from sentence_transformers import SentenceTransformer
import torch

CHROMA_DIR = "./chroma_db"
COLLECTION_NAME = "videos"
EMBED_MODEL = "sentence-transformers/all-MiniLM-L6-v2"


# ---------------------------------------------------
# CLIENT + EMBEDDINGS
# ---------------------------------------------------
def get_client():
    return PersistentClient(path=CHROMA_DIR)


def get_embedder():
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"[INFO] Embedding model on {device}")
    return SentenceTransformer(EMBED_MODEL, device=device)


# ---------------------------------------------------
# FIXED QUERY METHOD (NO MORE WHERE ERRORS)
# ---------------------------------------------------
def query_by_type(video_id, question, top_k=5):
    embedder = get_embedder()
    client = get_client()
    col = client.get_collection(COLLECTION_NAME)

    # Encode question
    q_emb = embedder.encode([question], convert_to_numpy=True).tolist()

    # ---------------------------------------------------
    # 1) Query transcription + frame (ALL documents for the video)
    # ---------------------------------------------------
    base = col.query(
        query_embeddings=q_emb,
        n_results=top_k * 4,              # get more so we can filter in python
        where={"video_id": video_id},     # ONLY ONE FIELD ALLOWED
        include=["documents", "metadatas", "distances"]
    )

    docs = base.get("documents", [[]])[0]
    metas = base.get("metadatas", [[]])[0]
    dists = base.get("distances", [[]])[0]

    transcript_hits = []
    frame_hits = []

    # ---------------------------------------------------
    # 2) Split transcript vs frame USING PYTHON
    # ---------------------------------------------------
    for doc, meta, dist in zip(docs, metas, dists):
        if meta["type"] == "transcript":
            transcript_hits.append({
                "document": doc,
                "metadata": meta,
                "distance": dist
            })
        elif meta["type"] == "frame":
            frame_hits.append({
                "document": doc,
                "metadata": meta,
                "distance": dist
            })

    # Limit top_k
    transcript_hits = transcript_hits[:top_k]
    frame_hits = frame_hits[:top_k]

    # ---------------------------------------------------
    # 3) Combine transcript + frame
    # ---------------------------------------------------
    combined = transcript_hits + frame_hits
    combined_sorted = sorted(
        combined,
        key=lambda x: x["distance"] if x["distance"] is not None else 9999
    )[:top_k]

    return {
        "transcript": transcript_hits,
        "frame": frame_hits,
        "combined_top": combined_sorted
    }


# ---------------------------------------------------
# CLI ENTRY
# ---------------------------------------------------
if __name__ == "__main__":
    import sys

    if len(sys.argv) < 3:
        print("Usage: python ts.py <video_id> <question> [top_k]")
        sys.exit()

    video_id = sys.argv[1]
    question = sys.argv[2]
    top_k = int(sys.argv[3]) if len(sys.argv) > 3 else 5

    out = query_by_type(video_id, question, top_k)

    print("\n========== TRANSCRIPT ==========\n")
    for r in out["transcript"]:
        print(r)

    print("\n========== FRAME (YOLO + OCR) ==========\n")
    

    print("\n========== COMBINED ==========\n")
    for r in out["combined_top"]:
        print(r)
