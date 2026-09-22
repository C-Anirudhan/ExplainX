# Backend/whisper_engine.py

import os
import json
import torch
from faster_whisper import WhisperModel


def run_whisper(audio_path, output_json_path=None):
    cuda_available = torch.cuda.is_available()
    device = "cuda" if cuda_available else "cpu"
    compute_type = "int8_float16" if cuda_available else "int8"

    print(
        f"[INFO] Loading Whisper on {device} ({compute_type})...",
        flush=True,
    )

    model = WhisperModel(
        "medium",
        device=device,
        compute_type=compute_type,
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
