import os
import json
import requests
from dotenv import load_dotenv

# Load .env variables
load_dotenv()

LANGBASE_API_KEY = os.getenv("LANGBASE_API_KEY")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "cohere:embed-multilingual-light-v3.0")

if not LANGBASE_API_KEY:
    raise ValueError("❌ LANGBASE_API_KEY missing in .env")

BASE_URL = "https://api.langbase.com/v1"

# LangBase memory limits
MAX_MEMORY_SIZE = 10 * 1024 * 1024        # 10 MB per memoryset
CHUNK_SIZE = 50 * 1024                    # 50 KB per chunk
MEMORY_PREFIX = "video_001_part_"         # memoryset names

headers = {
    "Authorization": f"Bearer {LANGBASE_API_KEY}",
    "Content-Type": "application/json"
}


# ---------------------------------------------------------
# CREATE MEMORYSET
# ---------------------------------------------------------
def create_memoryset(name: str):
    print(f"\n[+] Creating memoryset: {name}")

    payload = {
        "name": name,
        "embedding_model": EMBEDDING_MODEL
    }

    r = requests.post(f"{BASE_URL}/memorysets", json=payload, headers=headers)

    print("👉 STATUS:", r.status_code)
    print("👉 RAW RESPONSE:", r.text)

    try:
        response = r.json()
    except:
        raise RuntimeError("❌ Could not decode LangBase JSON response")

    # LangBase returns: {"name": "video_001_part_1", "url": "..."}
    if "name" not in response:
        raise RuntimeError(f"❌ Memory creation failed: {response}")

    memory_id = response["name"]
    print(f"[✓] Memoryset created → ID: {memory_id}")

    return memory_id


# ---------------------------------------------------------
# UPLOAD CHUNK AS MEMORY RECORD
# ---------------------------------------------------------
def upload_chunk(memory_id: str, text: str, metadata=None):
    payload = {
        "text": text,
        "metadata": metadata or {}
    }

    url = f"{BASE_URL}/memorysets/{memory_id}/records"
    r = requests.post(url, json=payload, headers=headers)

    if r.status_code >= 400:
        print("❌ UPLOAD ERROR:", r.text)
        raise RuntimeError("Chunk upload failed")

    return r.json()


# ---------------------------------------------------------
# MAIN FUNCTION — SPLIT & UPLOAD JSON
# ---------------------------------------------------------
def split_and_upload(json_file_path):
    print("[INFO] Loading JSON:", json_file_path)

    with open(json_file_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    json_str = json.dumps(data, ensure_ascii=False)
    total_bytes = len(json_str.encode("utf-8"))

    print(f"[INFO] JSON Size: {total_bytes/1024/1024:.2f} MB")

    # -------- Split into 50KB chunks --------
    print("[INFO] Splitting JSON into 50KB chunks...")
    chunks = []
    idx = 0
    while idx < len(json_str):
        chunks.append(json_str[idx:idx + CHUNK_SIZE])
        idx += CHUNK_SIZE

    print(f"[INFO] Total chunks created: {len(chunks)}")

    # -------- Create first memoryset --------
    memory_index = 1
    memory_id = create_memoryset(f"{MEMORY_PREFIX}{memory_index}")

    used_bytes = 0

    # -------- Upload chunks --------
    for i, chunk in enumerate(chunks):
        chunk_size = len(chunk.encode("utf-8"))

        # If the memoryset hits 10MB → create new memoryset
        if used_bytes + chunk_size > MAX_MEMORY_SIZE:
            print("\n[!] 10MB limit reached → creating new memoryset...\n")
            memory_index += 1
            memory_id = create_memoryset(f"{MEMORY_PREFIX}{memory_index}")
            used_bytes = 0

        print(f"[UPLOAD] Chunk {i+1}/{len(chunks)} → Memoryset: {memory_id}")

        upload_chunk(
            memory_id,
            chunk,
            metadata={
                "chunk": i + 1,
                "total_chunks": len(chunks)
            }
        )

        used_bytes += chunk_size

    print("\n[✓] UPLOAD COMPLETE!")
    print(f"[✓] Total memorysets created: {memory_index}")
    print("[✓] Your video is now fully stored in LangBase!")


# ---------------------------------------------------------
# RUN SCRIPT
# ---------------------------------------------------------
if __name__ == "__main__":
    split_and_upload("./langbase_json/video_unified.json")
