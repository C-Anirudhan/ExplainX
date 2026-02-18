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
    return SentenceTransformer(EMBED_MODEL, device=device,trust_remote_code=True)

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
# SAFE, CONTRACT-LOCKED RETRIEVER
# ---------------------------------------------------
def retrieve_combined(video_id: str, question: str, top_k_transcript=10, top_k_frames=10):
    question = str(question)
    # 🔐 Hard type safety
    video_id = str(video_id)
    question = str(question)

    client = get_client()
    col = client.get_collection(COLLECTION_NAME)
    embedder = SentenceTransformer(EMBED_MODEL)


    q_emb = embedder.encode([question], convert_to_numpy=True).tolist()

    # ----------------------------- TRANSCRIPTS
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

    # ----------------------------- FRAMES
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

    # ----------------------------- FORMAT
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
