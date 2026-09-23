import torch
import cv2 as cv
import os
from typing import List, Tuple

try:
    import easyocr
except ImportError:
    easyocr = None


class OCRDetector:
    def __init__(self, langs: List[str] = ['en'], crop_ratio: float = 0.40, downscale: float = 0.7):
        self.crop_ratio = crop_ratio
        self.downscale = downscale
        self.reader = None

        if easyocr is None:
            print("[INFO] easyocr not installed. OCR running in stub mode.")
            return

        try:
            self.device = 0 if torch.cuda.is_available() else -1
            self.reader = easyocr.Reader(lang_list=langs, gpu=(self.device == 0))
            print(f"OCR initialized: GPU={'yes' if self.device==0 else 'no'}")
        except Exception as e:
            print(f"[WARN] Failed to initialize easyocr: {e}")
            self.reader = None

    def read_frame(self, frame, force_full=False):
        if not self.reader:
            return []

        h, w = frame.shape[:2]

        if not force_full:
            crop_start = int(h * (1 - self.crop_ratio))
            frame_crop = frame[crop_start:h, :]
            y_offset = crop_start
        else:
            frame_crop = frame
            y_offset = 0

        if self.downscale != 1.0:
            frame_crop = cv.resize(frame_crop, None, fx=self.downscale, fy=self.downscale,
                                   interpolation=cv.INTER_LINEAR)

        img = cv.cvtColor(frame_crop, cv.COLOR_BGR2RGB)

        results = self.reader.readtext(img)

        parsed = []
        for (bbox_pts, text, conf) in results:
            text = str(text)
            scaled_pts = []
            for pt in bbox_pts:
                x = int(float(pt[0]) / self.downscale)
                y = int(float(pt[1]) / self.downscale)
                scaled_pts.append((x, y + y_offset))

            x_coords = [int(p[0]) for p in scaled_pts]
            y_coords = [int(p[1]) for p in scaled_pts]

            x1 = int(min(x_coords))
            y1 = int(min(y_coords))
            x2 = int(max(x_coords))
            y2 = int(max(y_coords))

            parsed.append(
                (text, float(conf), (x1, y1, x2, y2))
            )

        return parsed

    def draw_ocr(self, frame, ocr_results, color=(0,165,255)):
        for text, conf, (x1, y1, x2, y2) in ocr_results:
            cv.rectangle(frame, (x1, y1), (x2, y2), color, 1)
            label = f"{text} {conf:.2f}"
            cv.putText(frame, label, (x1, max(y1 - 8, 0)),
                       cv.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)

    def save_results(self, out_path: str, frame_index: int, ocr_results):
        os.makedirs(os.path.dirname(out_path), exist_ok=True)
        with open(out_path, "a", encoding="utf-8") as f:
            f.write(f"Frame {int(frame_index)}:\n")
            for text, conf, (x1, y1, x2, y2) in ocr_results:
                f.write(f"\t{text}\t{float(conf):.3f}\t({int(x1)},{int(y1)},{int(x2)},{int(y2)})\n")
            f.write("\n")
