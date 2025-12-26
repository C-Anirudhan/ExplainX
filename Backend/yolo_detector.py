from ultralytics import YOLO
import cv2 as cv
import torch


class YOLOv8Detector:
    def __init__(self, model_name="yolov8n.pt"):
        print(f"Loading YOLOv8 model: {model_name} ...")

        self.model = YOLO(model_name)

        self.last_results = []

        if torch.cuda.is_available():
            self.device = "cuda"
            print("CUDA detected. Running on GPU.")
            self.model.to(self.device)
        else:
            self.device = "cpu"
            print("CUDA not found. Running on CPU.")

        print("Model loaded successfully.\n")


    def detect(self, frame):
        # Reset last detections
        self.last_results = []

        # Run inference
        results = self.model(
            frame,
            imgsz=480,
            half=(self.device == "cuda"),
            verbose=False
        )[0]

        # Loop detections
        for box in results.boxes:
            xyxy = box.xyxy[0].cpu().tolist()  # <-- JSON-SAFE PYTHON LIST

            x1 = int(xyxy[0])
            y1 = int(xyxy[1])
            x2 = int(xyxy[2])
            y2 = int(xyxy[3])

            conf = float(box.conf.cpu().numpy().item())
            cls = int(box.cls.cpu().numpy().item())
            label = str(results.names[cls])

            # Store JSON-safe output
            self.last_results.append({
                "label": label,
                "confidence": conf,
                "box": [x1, y1, x2, y2]
            })

            # Draw boxes
            cv.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
            cv.putText(
                frame,
                f"{label} {conf:.2f}",
                (x1, y1 - 6),
                cv.FONT_HERSHEY_SIMPLEX,
                0.6,
                (0, 255, 0),
                2
            )

        return frame


    def export_last_results(self):
        return self.last_results
