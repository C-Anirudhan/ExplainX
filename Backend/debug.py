from retrieve import retrieve_combined

# ----------- CONFIG FOR TESTING ----------
VIDEO_ID = "Lenovo Legion 7 RTX 3080 Unboxing !!.mp4"
QUESTION = "summarize the video fully"
TOP_K = 10
# -----------------------------------------

def main():
    print("\n[TEST] Running retrieval test...\n")

    combined_text, transcript_hits, frame_hits = retrieve_combined(
        VIDEO_ID,
        QUESTION,
        top_k_transcript=TOP_K,
        top_k_frames=TOP_K
    )

    print("\n====== COMBINED TEXT (for LLM) ======\n")
    print(combined_text)

    print("\n====== TRANSCRIPT HITS ======\n")
    for t in transcript_hits:
        print(t, "\n")

    print("\n====== FRAME HITS (YOLO + OCR) ======\n")
    for f in frame_hits:
        print(f, "\n")

if __name__ == "__main__":
    main()
