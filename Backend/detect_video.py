# Backend/detect_video.py

import cv2 as cv
from yolo_detector import YOLOv8Detector
from ocr_detector import OCRDetector
import os

VIDEO_PATH = "./Backend/downloads/Lenovo Legion 7 RTX 3080 Unboxing !!.mp4"
OUTPUT_OCR_FILE = "./frames/ocr_results.txt"
OCR_FRAME_INTERVAL = 15
SAVE_FRAMES_DIR = "./frames/annotated/"

def main():
    detector = YOLOv8Detector("yolov8n.pt")
    ocr = OCRDetector(langs=['en'])

    os.makedirs(SAVE_FRAMES_DIR, exist_ok=True)
    if os.path.exists(OUTPUT_OCR_FILE):
        os.remove(OUTPUT_OCR_FILE)

    cap = cv.VideoCapture(VIDEO_PATH)
    if not cap.isOpened():
        print("Error: unable to open video")
        return

    # ---- Output video writer ----
    width  = int(cap.get(cv.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv.CAP_PROP_FRAME_HEIGHT))
    fps    = cap.get(cv.CAP_PROP_FPS)

    fourcc = cv.VideoWriter_fourcc(*"mp4v")
    out = cv.VideoWriter("output.mp4", fourcc, fps, (width, height))

    frame_idx = 0

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        annotated = detector.detect(frame.copy())

        if frame_idx % OCR_FRAME_INTERVAL == 0:
            ocr_results = ocr.read_frame(frame)
            if ocr_results:
                ocr.draw_ocr(annotated, ocr_results)
                ocr.save_results(OUTPUT_OCR_FILE, frame_idx, ocr_results)

        # save annotated frame to output video
        out.write(annotated)

        # optionally save keyframes
        if frame_idx % (OCR_FRAME_INTERVAL * 2) == 0:
            cv.imwrite(f"{SAVE_FRAMES_DIR}/frame_{frame_idx:06d}.jpg", annotated)

        frame_idx += 1

    cap.release()
    out.release()
    print("Processing complete. Output saved as output.mp4")

if __name__ == "__main__":
    main()
