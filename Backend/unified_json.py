# Backend/unified_json.py

import json
import os

def save_unified_json(video_name, duration, fps, frame_results, transcript, output_path):
    """
    Saves YOLO + OCR + Whisper results into a single LangBase-friendly JSON.
    """
    data = {
        "video_name": video_name,
        "duration_seconds": duration,
        "fps": fps,
        "frames": frame_results,
        "transcript": transcript
    }

    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

    print(f"[INFO] Unified JSON saved at: {output_path}")
