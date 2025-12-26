# Backend/new_whisper.py
import os
import traceback


def run_whisper_process(_, audio_path, output_json_path):
    try:
        from whisper_engine import run_whisper

        audio_path = os.path.abspath(audio_path)
        output_json_path = os.path.abspath(output_json_path)

        print("[WHISPER] Audio path:", audio_path, flush=True)
        print("[WHISPER] Output JSON:", output_json_path, flush=True)

        if not os.path.exists(audio_path):
            raise FileNotFoundError(audio_path)

        # 🔥 JSON written INSIDE whisper_engine
        run_whisper(audio_path, output_json_path)

    except Exception as e:
        print("🔥 ERROR IN WHISPER PROCESS:", e, flush=True)
        traceback.print_exc()
