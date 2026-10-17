"""Download public object and face models to this installation."""
from pathlib import Path
import urllib.request

target=Path(__file__).parent/'models'
target.mkdir(exist_ok=True)
for folder,name in [('face_detection_yunet','face_detection_yunet_2023mar.onnx'),
                    ('face_recognition_sface','face_recognition_sface_2021dec.onnx')]:
    path=target/name
    if path.is_file() and path.stat().st_size > (100000 if 'detection' in folder else 38000000):
        print(name,'already present')
        continue
    temp=path.with_suffix('.download')
    urllib.request.urlretrieve('https://media.githubusercontent.com/media/opencv/opencv_zoo/main/models/'+folder+'/'+name,temp)
    temp.replace(path)
    print(name,'downloaded',path.stat().st_size,'bytes')

# Ultralytics downloads the published pretrained weights when absent.
from ultralytics import YOLO
YOLO(str(Path(__file__).resolve().parents[1] / 'yolov8n.pt'))
print('YOLOv8n object model ready')
