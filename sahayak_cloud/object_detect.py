import cv2
from ultralytics import YOLO

model = YOLO("yolov8n.pt")

def detect_objects(image_path):
    image = cv2.imread(image_path)

    if image is None:
        return []

    results = model(image, conf=0.5)

    labels = []

    if len(results[0].boxes) > 0:
        for box in results[0].boxes:
            cls_id = int(box.cls[0])
            label = model.names[cls_id]
            labels.append(label)

    return labels