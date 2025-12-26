# Backend/whisper_engine.py

import os
import json
from faster_whisper import WhisperModel


def run_whisper(audio_path, output_json_path=None):
    print("[INFO] Loading Whisper (medium FP16 GPU)...")

    model = WhisperModel(
        "medium",
        device="cuda",
        compute_type="int8_float16"
    )

    print("[INFO] Transcribing...")

    segments, info = model.transcribe(
        audio_path,
        language="en",
        beam_size=5
    )

    results = []

    for seg in segments:
        results.append({
            "start": float(seg.start),
            "end": float(seg.end),
            "text": seg.text.strip()
        })

    print(f"[INFO] Whisper transcription complete. Segments={len(results)}")

    # 🔥 WRITE JSON HERE (CRITICAL FIX)
    if output_json_path:
        os.makedirs(os.path.dirname(output_json_path), exist_ok=True)

        with open(output_json_path, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
            f.flush()
            os.fsync(f.fileno())

        print("[INFO] Whisper JSON written successfully")

    return results
