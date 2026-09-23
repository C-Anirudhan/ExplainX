# Backend/whisper_engine.py
# Uses Groq API with whisper-large-v3-turbo for lightning-fast transcription
# Falls back to local whisper if Groq is unavailable

import os
import json
import traceback


def run_whisper(audio_path, output_json_path=None):
    """
    Transcribe audio using Groq's whisper-large-v3-turbo API.
    Returns list of segments: [{"start": float, "end": float, "text": str}, ...]
    Writes JSON to output_json_path if provided.
    """
    results = []

    # Strategy 1: Groq API (fast, ~2 seconds for 4-min video)
    try:
        from dotenv import load_dotenv
        load_dotenv(override=True)

        groq_key = os.getenv("GROQ_API_KEY")
        if not groq_key:
            # Check generic API key
            generic = os.getenv("API_KEY") or os.getenv("API")
            if generic and generic.startswith("gsk_"):
                groq_key = generic

        if groq_key:
            from groq import Groq
            client = Groq(api_key=groq_key)

            print(f"[WHISPER] Transcribing via Groq API: {audio_path}", flush=True)

            with open(audio_path, "rb") as f:
                response = client.audio.transcriptions.create(
                    file=(os.path.basename(audio_path), f),
                    model="whisper-large-v3-turbo",
                    response_format="verbose_json",
                )

            segments = getattr(response, 'segments', None)
            if segments is None and isinstance(response, dict):
                segments = response.get('segments', [])

            if segments:
                for seg in segments:
                    if isinstance(seg, dict):
                        results.append({
                            "start": float(seg.get("start", 0.0)),
                            "end": float(seg.get("end", 0.0)),
                            "text": str(seg.get("text", "")).strip()
                        })
                    else:
                        results.append({
                            "start": float(getattr(seg, "start", 0.0)),
                            "end": float(getattr(seg, "end", 0.0)),
                            "text": str(getattr(seg, "text", "")).strip()
                        })
            elif hasattr(response, 'text') and response.text:
                results.append({"start": 0.0, "end": 0.0, "text": str(response.text).strip()})
            elif isinstance(response, dict) and response.get('text'):
                results.append({"start": 0.0, "end": 0.0, "text": str(response.get('text')).strip()})

            print(f"[WHISPER] Groq transcription complete. Segments={len(results)}", flush=True)
        else:
            print("[WHISPER] No Groq API key found, skipping Groq...", flush=True)
            raise RuntimeError("No Groq key")

    except Exception as e:
        print(f"[WHISPER] Groq API failed: {e}", flush=True)

        # Strategy 2: Try faster_whisper locally (if installed)
        try:
            import torch
            from faster_whisper import WhisperModel

            cuda_available = torch.cuda.is_available()
            device = "cuda" if cuda_available else "cpu"
            compute_type = "int8_float16" if cuda_available else "int8"

            print(f"[WHISPER] Falling back to local faster_whisper on {device}", flush=True)

            model = WhisperModel("medium", device=device, compute_type=compute_type)
            segments, info = model.transcribe(audio_path, language="en", beam_size=5)

            for seg in segments:
                results.append({
                    "start": float(seg.start),
                    "end": float(seg.end),
                    "text": seg.text.strip()
                })

            print(f"[WHISPER] Local transcription complete. Segments={len(results)}", flush=True)

        except ImportError:
            print("[WHISPER] faster_whisper not installed. No transcription available.", flush=True)
            traceback.print_exc()
        except Exception as e2:
            print(f"[WHISPER] Local whisper also failed: {e2}", flush=True)
            traceback.print_exc()

    # Write JSON output
    if output_json_path and results:
        os.makedirs(os.path.dirname(output_json_path), exist_ok=True)
        with open(output_json_path, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
            f.flush()
            os.fsync(f.fileno())
        print(f"[WHISPER] JSON written: {output_json_path} ({len(results)} segments)", flush=True)
    elif output_json_path and not results:
        # Write empty array so downstream doesn't crash
        os.makedirs(os.path.dirname(output_json_path), exist_ok=True)
        with open(output_json_path, "w", encoding="utf-8") as f:
            json.dump([], f)
        print("[WHISPER] No segments produced, wrote empty JSON", flush=True)

    return results
