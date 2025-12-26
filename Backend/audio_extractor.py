# Backend/audio_extractor.py

import subprocess
import os

def extract_audio(video_path, out_path="./frames/audio.wav"):
    os.makedirs(os.path.dirname(out_path), exist_ok=True)

    cmd = [
        "ffmpeg",
        "-y",
        "-i", video_path,
        "-vn",
        "-ac", "1",
        "-ar", "16000",
        out_path
    ]

    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return out_path
