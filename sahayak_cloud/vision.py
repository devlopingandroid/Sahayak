"""YOLO + YuNet/SFace inference, with reviewed enrollment."""
import threading
import os
from pathlib import Path
import cv2
import numpy as np


class Vision:
    def __init__(self, base, store):
        self.base, self.store = Path(base), store
        self.lock = threading.RLock()
        self.yolo = self.objects = self.detector = self.recognizer = None
        self.error = None
        self.ready = False
        self.labels = []

    def load(self):
        try:
            model_dir = self.base / 'sahayak_cloud/models'
            if os.environ.get('SAHAYAK_CLOUD')=='1':
                from objects_onnx import ObjectDetector
                cv2.setNumThreads(1)
                self.objects = ObjectDetector(model_dir)
                self.labels = self.objects.names
            else:
                from ultralytics import YOLO
                self.yolo = YOLO(str(self.base / 'yolov8n.pt'))
                self.labels = list(self.yolo.names.values())
            self.detector = cv2.FaceDetectorYN.create(str(model_dir / 'face_detection_yunet_2023mar.onnx'), '', (320, 320), .85)
            self.recognizer = cv2.FaceRecognizerSF.create(str(model_dir / 'face_recognition_sface_2021dec.onnx'), '')
            if os.environ.get('SAHAYAK_CLOUD')=='1':
                self.objects.detect(np.zeros((640,640,3),dtype=np.uint8))
            self.ready = True
        except Exception as exc:
            self.error = str(exc)

    def faces(self, image):
        # Fixed-size input also supports OpenCV 5's static ONNX input dimensions.
        resized = cv2.resize(image, (320, 320))
        _, faces = self.detector.detect(resized)
        result = []
        for face in faces if faces is not None else []:
            aligned = self.recognizer.alignCrop(resized, face)
            feature = self.recognizer.feature(aligned).flatten()
            feature = feature / max(np.linalg.norm(feature), 1e-8)
            result.append((face, feature))
        return result

    def enrollment(self, image):
        if not self.ready:
            raise ValueError('Vision models are not ready. Check system status.')
        with self.lock:
            faces = self.faces(image)
        if len(faces) != 1:
            raise ValueError('Use a clear photo containing exactly one face.')
        face, feature = faces[0]
        if min(face[2], face[3]) < 35:
            raise ValueError('Move closer to the camera so the face is larger.')
        return feature.tolist()

    def infer(self, image):
        if not self.ready:
            raise RuntimeError(self.error or 'Models are still loading')
        import json
        with self.lock:
            if self.objects is not None:
                detections = self.objects.detect(image)
            else:
                result = self.yolo(image, conf=.45, imgsz=640, verbose=False)[0]
                detections = []
                for box in result.boxes:
                    detections.append({'label': self.yolo.names[int(box.cls[0])],
                                       'score': round(float(box.conf[0]), 3),
                                       'box': [round(float(v), 1) for v in box.xyxy[0]]})
            samples = self.store.rows('''SELECT s.embedding,p.id,p.name,p.relationship,p.introduction FROM samples s
                JOIN people p ON p.id=s.person_id WHERE s.approved=1 AND p.deleted=0''')
            people = []
            threshold = float(self.store.get('face_threshold', .5))
            for face, feature in self.faces(image):
                scores = {}
                for sample in samples:
                    score = float(np.dot(feature, np.array(json.loads(sample['embedding']), dtype=np.float32)))
                    if sample['id'] not in scores or score > scores[sample['id']][0]:
                        scores[sample['id']] = (score, sample)
                ranked = sorted(scores.values(), key=lambda x: x[0], reverse=True)
                if ranked and ranked[0][0] >= threshold and (len(ranked) == 1 or ranked[0][0]-ranked[1][0] >= .06):
                    score, person = ranked[0]
                    if not any(p['id'] == person['id'] for p in people):
                        people.append({k: person[k] for k in ('id','name','relationship','introduction')}
                                      | {'score': round(score, 3)})
            return detections, people

    def enrollment_candidate(self, image):
        if not self.ready:
            raise ValueError('Wait for face recognition models to become ready.')
        with self.lock:
            faces = self.faces(image)
        if len(faces) != 1:
            raise ValueError('Keep exactly one person in the camera view.')
        face, feature = faces[0]
        if min(face[2], face[3]) < 45:
            raise ValueError('Move closer so your face is clearly visible.')
        scaled = cv2.resize(image, (320, 320))
        x, y, w, h = [int(v) for v in face[:4]]
        crop = scaled[max(0,y):min(320,y+h), max(0,x):min(320,x+w)]
        if not crop.size:
            raise ValueError('Keep your whole face inside the picture.')
        gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
        if not 35 <= float(gray.mean()) <= 220:
            raise ValueError('Improve the lighting; avoid very dark or overexposed photos.')
        if cv2.Laplacian(gray, cv2.CV_64F).var() < 45:
            raise ValueError('Hold still briefly; this face photo looks blurred.')
        small = cv2.resize(gray, (9,8))
        return {'feature': feature, 'hash': (small[:,1:] > small[:,:-1]).flatten()}
