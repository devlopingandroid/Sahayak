"""Build-time model export; PyTorch is not needed in the runtime image."""
import json
from pathlib import Path
from ultralytics import YOLO

root = Path(__file__).resolve().parents[1]
model = YOLO(str(root / 'yolov8n.pt'))
output = Path(model.export(format='onnx', imgsz=640, batch=1, opset=12,
                         dynamic=False, simplify=False, nms=False, device='cpu'))
target = root / 'sahayak_cloud/models'
target.mkdir(exist_ok=True)
output.replace(target / 'yolov8n.onnx')
(target / 'object_labels.json').write_text(json.dumps(list(model.names.values())))
