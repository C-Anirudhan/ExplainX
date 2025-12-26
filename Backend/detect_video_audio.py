# Backend/detect_video_audio.py

import cv2 as cv
import os
import copy
import json
import traceback
import subprocess
from multiprocessing import Process, freeze_support

from yolo_detector import YOLOv8Detector
from ocr_detector import OCRDetector
from unified_json import save_unified_json
from new_whisper import run_whisper_process


class gen_json:
    def __init__(self, name):
        self.video_name = name

        # ---- Project root (absolute, multiprocessing-safe) ----
        self.BASE_DIR = os.path.abspath(os.getcwd())

        # ---- Paths ----
        self.VIDEO_PATH = os.path.join(self.BASE_DIR, "downloads", name)

        self.OUTPUT_JSON = os.path.join(
            self.BASE_DIR,
            "langbase_json",
            f"{name}.json"
        )

        self.SAVE_FRAMES_DIR = os.path.join(
            self.BASE_DIR,
            "frames",
            "annotated"
        )

        self.AUDIO_PATH = os.path.join(
            self.BASE_DIR,
            "frames",
            "audio.wav"
        )

        base = os.path.splitext(name)[0]
        self.WHISPER_JSON = os.path.join(
            self.BASE_DIR,
            "temp",
            f"{base}_whisper.json"
        )

        self.FRAME_STRIDE = 2        # skip 1 frame → ~15 FPS
        self.OCR_INTERVAL = 15       # OCR every 15 processed frames

    # ------------------------------------------------------------------
    def run_whisper_separately(self, timeout=1800):
        os.makedirs(os.path.dirname(self.WHISPER_JSON), exist_ok=True)

        if os.path.exists(self.WHISPER_JSON):
            os.remove(self.WHISPER_JSON)

        print("[INFO] Launching Whisper in isolated process…", flush=True)
        print("[DEBUG] Audio path:", self.AUDIO_PATH, flush=True)
        print("[DEBUG] Whisper JSON path:", self.WHISPER_JSON, flush=True)

        p = Process(
            target=run_whisper_process,
            args=(None, self.AUDIO_PATH, self.WHISPER_JSON)
        )

        p.start()
        p.join(timeout)

        if p.is_alive():
            print("[WARN] Whisper timeout → killing", flush=True)
            p.terminate()
            p.join()
            return []

        if not os.path.exists(self.WHISPER_JSON):
            print("[WARN] Whisper produced NO JSON", flush=True)
            return []

        try:
            with open(self.WHISPER_JSON, "r", encoding="utf-8") as f:
                transcript = json.load(f)
                print("[INFO] Whisper JSON loaded successfully", flush=True)
                return transcript
        except Exception:
            print("🔥 ERROR loading Whisper JSON")
            traceback.print_exc()
            return []

    # ------------------------------------------------------------------
    def _extract_audio(self):
        """Extract audio using FFmpeg"""
        os.makedirs(os.path.dirname(self.AUDIO_PATH), exist_ok=True)
        print(f"[INFO] Extracting audio → {self.AUDIO_PATH}", flush=True)

        ffmpeg_command = [
            "ffmpeg",
            "-y",
            "-i", self.VIDEO_PATH,
            "-vn",
            "-acodec", "pcm_s16le",
            "-ac", "1",
            self.AUDIO_PATH
        ]

        try:
            subprocess.run(
                ffmpeg_command,
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            print("[INFO] Audio extraction successful", flush=True)
            return True

        except subprocess.CalledProcessError as e:
            print("[ERROR] FFmpeg failed", flush=True)
            print(e.stderr.decode(), flush=True)
            return False

        except FileNotFoundError:
            print("[ERROR] FFmpeg not found in PATH", flush=True)
            return False

    # ------------------------------------------------------------------
    def main(self):
        try:
            # ---- Create directories ----
            os.makedirs(self.SAVE_FRAMES_DIR, exist_ok=True)
            os.makedirs(os.path.dirname(self.OUTPUT_JSON), exist_ok=True)
            os.makedirs(os.path.dirname(self.WHISPER_JSON), exist_ok=True)

            print(f"\n[INFO] Processing video: {self.VIDEO_PATH}", flush=True)

            # ---- Extract audio ----
            if not self._extract_audio():
                print("[FATAL] Audio extraction failed. Aborting.", flush=True)
                return None

            if not os.path.exists(self.AUDIO_PATH):
                print("[FATAL] Audio file not found after extraction", flush=True)
                return None

            # ---- STEP 1: Whisper ----
            transcript = self.run_whisper_separately()

            # ---- STEP 2: Load models ----
            print("[INFO] Loading YOLO + OCR", flush=True)
            detector = YOLOv8Detector("yolov8n.pt")
            ocr = OCRDetector(langs=["en"])

            # ---- STEP 3: Open video ----
            cap = cv.VideoCapture(self.VIDEO_PATH)
            if not cap.isOpened():
                print("[ERROR] Failed to open video", flush=True)
                return None

            fps = cap.get(cv.CAP_PROP_FPS)
            total_frames = int(cap.get(cv.CAP_PROP_FRAME_COUNT))
            duration_sec = total_frames / fps if fps > 0 else 0

            print(f"[INFO] FPS={fps}, Duration={duration_sec}s", flush=True)

            # ---- STEP 4: Frame processing ----
            frames_output = []
            frame_idx = 0
            ocr_counter = 0
            last_percent = -1

            print("[INFO] Running YOLO + OCR…", flush=True)

            while True:
                cap.set(cv.CAP_PROP_POS_FRAMES, frame_idx)
                ret, frame = cap.read()

                if not ret:
                    break

                percent = int((frame_idx / total_frames) * 100)
                if percent != last_percent:
                    print(f"[INFO] {percent}% ({frame_idx}/{total_frames})", flush=True)
                    last_percent = percent

                timestamp = frame_idx / fps
                annotated = frame.copy()

                # YOLO
                detector.detect(annotated)
                yolo_data = copy.deepcopy(detector.export_last_results())

                # OCR
                ocr_list = []
                if ocr_counter % self.OCR_INTERVAL == 0:
                    res = ocr.read_frame(frame)
                    if res:
                        ocr.draw_ocr(annotated, res)
                        for text, conf, box in res:
                            ocr_list.append({
                                "text": str(text),
                                "confidence": float(conf),
                                "box": [int(x) for x in box]
                            })

                ocr_counter += 1

                frames_output.append({
                    "frame_index": frame_idx,
                    "timestamp": timestamp,
                    "yolo_objects": yolo_data,
                    "ocr": ocr_list
                })

                frame_idx += self.FRAME_STRIDE

            cap.release()
            print("[INFO] YOLO + OCR finished", flush=True)

            # ---- STEP 5: Save unified JSON ----
            save_unified_json(
                video_name=self.video_name,
                duration=duration_sec,
                fps=fps,
                frame_results=frames_output,
                transcript=transcript,
                output_path=self.OUTPUT_JSON
            )

            print("[INFO] Final JSON saved:", self.OUTPUT_JSON, flush=True)
            return self.OUTPUT_JSON

        except Exception:
            print("🔥 ERROR IN detect_video_audio.main()")
            traceback.print_exc()
            return None

    def execjson(self):
        return self.main()


# ----------------------------------------------------------------------
# Windows multiprocessing entry
# ----------------------------------------------------------------------
if __name__ == "__main__":
    freeze_support()
    name = input("Enter filename inside downloads/: ").strip()
    print(gen_json(name).execjson())
