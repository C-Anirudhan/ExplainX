import torch
from chromadb import PersistentClient
from sentence_transformers import SentenceTransformer

CHROMA_DIR = "./chroma_db"
COLLECTION_NAME = "videos"
EMBED_MODEL = "sentence-transformers/all-MiniLM-L6-v2"

# ---------------------------------------------------
# Load embedder
# ---------------------------------------------------
def get_embedder():
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"[INFO] Embeddings on {device}")
    return SentenceTransformer(EMBED_MODEL, device=device)

# ---------------------------------------------------
# Connect to Chroma
# ---------------------------------------------------
def get_client():
    return PersistentClient(path=CHROMA_DIR)

# ---------------------------------------------------
# Convert result list into clean text for LLM
# ---------------------------------------------------
def format_results(results, header):
    out = f"\n\n===== {header} =====\n"
    for r in results:
        out += f"\n• {r['document']}"
    return out


# ---------------------------------------------------
# Retrieve transcript + frame results separately
# ---------------------------------------------------
def retrieve_combined(video_id, question, top_k_transcript=10, top_k_frames=10):
    client = get_client()
    col = client.get_collection(COLLECTION_NAME)
    embedder = get_embedder()

    q_emb = embedder.encode([question], convert_to_numpy=True).tolist()

    # -----------------------------
    # SEARCH TRANSCRIPT SEGMENTS
    # -----------------------------
    transcript_results = col.query(
        query_embeddings=q_emb,
        n_results=top_k_transcript,
        where={
            "$and": [
                {"video_id": {"$eq": video_id}},
                {"type": {"$eq": "transcript"}}
            ]
        },
        include=["documents", "metadatas", "distances"]
    )

    tr_docs = transcript_results["documents"][0]
    tr_meta = transcript_results["metadatas"][0]
    tr_dist = transcript_results["distances"][0]

    transcript_hits = [
        {"document": tr_docs[i], "metadata": tr_meta[i], "distance": tr_dist[i]}
        for i in range(len(tr_docs))
    ]

    # -----------------------------
    # SEARCH FRAME YOLO + OCR DOCS
    # -----------------------------
    frame_results = col.query(
        query_embeddings=q_emb,
        n_results=top_k_frames,
        where={
            "$and": [
                {"video_id": {"$eq": video_id}},
                {"type": {"$eq": "frame"}}
            ]
        },
        include=["documents", "metadatas", "distances"]
    )

    fr_docs = frame_results["documents"][0]
    fr_meta = frame_results["metadatas"][0]
    fr_dist = frame_results["distances"][0]

    frame_hits = [
        {"document": fr_docs[i], "metadata": fr_meta[i], "distance": fr_dist[i]}
        for i in range(len(fr_docs))
    ]

    # -----------------------------
    # Combine readable text
    # -----------------------------
    formatted_transcript = format_results(transcript_hits, "TRANSCRIPT SEGMENTS")
    formatted_frames = format_results(frame_hits, "VISUAL (YOLO + OCR) FRAMES")

    combined_text = (
        "You are analyzing a video.\n"
        "Below are two types of retrieved context:\n"
        "1️⃣ Transcript segments (spoken content)\n"
        "2️⃣ Frame descriptions (YOLO objects + OCR text)\n\n"
        "Use BOTH to answer the question.\n\n"
        f"{formatted_transcript}\n\n{formatted_frames}"
    )

    return combined_text, transcript_hits, frame_hits




# ---------------------------------------------------
# CLI usage (manual testing)
# ---------------------------------------------------
if __name__ == "__main__":
    import sys

    video_id = sys.argv[1]
    question = sys.argv[2]
    top_k = int(sys.argv[3]) if len(sys.argv) > 3 else 10

    combined_text, tr, fr = retrieve_combined(video_id, question, top_k, top_k)

    print("\n========== COMBINED OUTPUT ==========\n")
    print(combined_text)
