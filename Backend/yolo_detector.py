import os
import cv2 as cv
import torch

try:
    from ultralytics import YOLO
except ImportError:
    YOLO = None


class YOLOv8Detector:
    def __init__(self, model_name="yolov8n.pt"):
        self.last_results = []
        if YOLO is None:
            print("[INFO] ultralytics not installed. YOLO detector running in stub mode.")
            self.model = None
            return

        try:
            print(f"Loading YOLOv8 model: {model_name} ...")
            self.model = YOLO(model_name)
            if torch.cuda.is_available():
                self.device = "cuda"
                self.model.to(self.device)
            else:
                self.device = "cpu"
            print("Model loaded successfully.\n")
        except Exception as e:
            print(f"[WARN] Failed to load YOLO model: {e}")
            self.model = None

    def detect(self, frame):
        if not self.model:
            self.last_results = []
            return []

        results = self.model(frame, verbose=False)
        self.last_results = []

        for r in results:
            boxes = r.boxes
            for box in boxes:
                cls_id = int(box.cls[0])
                label = self.model.names[cls_id]
                conf = float(box.conf[0])
                coords = [int(x) for x in box.xyxy[0]]

                self.last_results.append({
                    "label": label,
                    "confidence": conf,
                    "box": coords
                })

        return self.last_results

    def export_last_results(self):
        return self.last_results
