"""YOLOv8n inference without importing PyTorch in small cloud containers."""
import json
from pathlib import Path

import cv2
import numpy as np


class ObjectDetector:
    def __init__(self, model_dir):
        model_dir = Path(model_dir)
        self.names = json.loads((model_dir / 'object_labels.json').read_text())
        self.net = cv2.dnn.readNetFromONNX(str(model_dir / 'yolov8n.onnx'))
        self.net.setPreferableBackend(cv2.dnn.DNN_BACKEND_OPENCV)
        self.net.setPreferableTarget(cv2.dnn.DNN_TARGET_CPU)

    @staticmethod
    def prepare(image):
        height, width = image.shape[:2]
        scale = min(640 / height, 640 / width)
        resized_w, resized_h = round(width * scale), round(height * scale)
        left = round((640 - resized_w) / 2 - .1)
        top = round((640 - resized_h) / 2 - .1)
        resized = cv2.resize(image, (resized_w, resized_h))
        padded = cv2.copyMakeBorder(resized, top, 640-resized_h-top,
                                   left, 640-resized_w-left,
                                   cv2.BORDER_CONSTANT, value=(114,114,114))
        blob = cv2.dnn.blobFromImage(padded, 1/255, (640,640), swapRB=True)
        return blob, scale, left, top

    def decode(self, output, shape, scale, left, top, confidence=.45):
        rows = output[0].T
        if rows.shape[1] != 4 + len(self.names):
            raise ValueError('Unexpected YOLOv8 ONNX output shape')
        classes = rows[:,4:].argmax(axis=1)
        scores = rows[np.arange(len(rows)), classes+4]
        mask = scores >= confidence
        rows, classes, scores = rows[mask], classes[mask], scores[mask]
        boxes = rows[:,:4].copy()
        boxes[:,:2] -= boxes[:,2:] / 2
        keep = []
        # Class-specific NMS preserves overlapping objects of different types.
        for cls in np.unique(classes):
            indices = np.flatnonzero(classes == cls)
            selected = cv2.dnn.NMSBoxes(boxes[indices].tolist(), scores[indices].tolist(),
                                        confidence, .7, top_k=300)
            keep.extend(indices[np.asarray(selected,dtype=int).reshape(-1)].tolist())
        keep.sort(key=lambda i: float(scores[i]), reverse=True)
        height, width = shape[:2]
        detections = []
        for index in keep[:300]:
            x,y,w,h = boxes[index]
            xyxy = [(x-left)/scale,(y-top)/scale,(x+w-left)/scale,(y+h-top)/scale]
            xyxy = np.clip(xyxy, [0,0,0,0], [width,height,width,height])
            detections.append({'label': self.names[int(classes[index])],
                               'score': round(float(scores[index]),3),
                               'box': [round(float(v),1) for v in xyxy]})
        return detections

    def detect(self, image):
        blob, scale, left, top = self.prepare(image)
        self.net.setInput(blob)
        return self.decode(self.net.forward(), image.shape, scale, left, top)
