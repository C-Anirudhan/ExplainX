import chromadb
from chromadb import PersistentClient
from sentence_transformers import SentenceTransformer
import torch

CHROMA_DIR = "./chroma_db"
COLLECTION_NAME = "videos"
EMBED_MODEL = "sentence-transformers/all-MiniLM-L6-v2"

def get_client():
    return PersistentClient(path=CHROMA_DIR)

def get_embedder():
    device = "cuda" if torch.cuda.is_available() else "cpu"
    return SentenceTransformer(EMBED_MODEL, device=device)

def query_frames(video_id, question, top_k=10):
    embedder = get_embedder()
    client = get_client()
    col = client.get_collection(COLLECTION_NAME)

    q_emb = embedder.encode([question], convert_to_numpy=True).tolist()

    where = {
        "video_id": video_id,
        "type": "frame"
    }

    results = col.query(
        query_embeddings=q_emb,
        n_results=top_k,
        where=where,
        include=["documents", "metadatas", "distances"]
    )

    docs = results.get("documents", [[]])[0]
    metas = results.get("metadatas", [[]])[0]
    dists = results.get("distances", [[]])[0]

    print("\n========== FRAME RESULTS ==========\n")

    for i in range(len(docs)):
        print(f"[{i+1}] distance={dists[i]:.4f}")
        print(" metadata:", metas[i])
        print(" document:", docs[i][:300])
        print("-----------------------------------\n")

