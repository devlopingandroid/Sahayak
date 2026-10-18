# SAHAYAK Models and Inference

The pipeline runs on the backend host in [`sahayak_cloud/vision.py`](sahayak_cloud/vision.py). The ESP32 captures and uploads images; it does not run these models.

Cloud mode uses `sahayak_cloud/objects_onnx.py` and OpenCV DNN for exported YOLOv8n ONNX, with no PyTorch import at runtime. Local mode uses Ultralytics and the original weights. Both retain the face models below. `deploy/export_object_model.py` exports static 640-pixel input, opset 12 and the label catalogue during the Docker build. Preprocessing uses aspect-preserving letterboxing, RGB normalization, class-specific NMS and image-coordinate restoration. See [cloud verification](deploy/CLOUD.md).

## Model inventory

| Task | Model/runtime | Local asset | Current configuration |
| --- | --- | --- | --- |
| Object detection | YOLOv8n through Ultralytics | `yolov8n.pt` in the repository root | Confidence threshold `0.45`, inference image size `640` |
| Face detection | OpenCV YuNet | `sahayak_cloud/models/face_detection_yunet_2023mar.onnx` | Image resized to `320 x 320`, detection score threshold `0.85` |
| Face representation | OpenCV SFace | `sahayak_cloud/models/face_recognition_sface_2021dec.onnx` | Aligned face embedding, normalized to unit length |
| Face matching | NumPy cosine similarity | Approved sample embeddings in SQLite | Default threshold `0.50`, minimum separation from the runner-up identity `0.06` |

These values come from the implementation, not from an accuracy benchmark. The face threshold can be changed between `0.35` and `0.90` in Settings. The other listed thresholds are currently code constants.

## Model installation

From the repository root:

```bash
python -m pip install -r sahayak_cloud/requirements.txt
python sahayak_cloud/download_models.py
```

The setup script downloads the OpenCV Zoo face models and prepares YOLOv8n through Ultralytics. Model weights are ignored by Git. Enrollment photos, embeddings and runtime databases are also excluded from the repository.

Upstream references:

- [Ultralytics YOLOv8 documentation](https://docs.ultralytics.com/models/yolov8/)
- [OpenCV Zoo YuNet](https://github.com/opencv/opencv_zoo/tree/main/models/face_detection_yunet)
- [OpenCV Zoo SFace](https://github.com/opencv/opencv_zoo/tree/main/models/face_recognition_sface)

The face downloader uses the named files from the upstream `main` branch and performs a file-size check. It does not currently pin a repository revision or verify a cryptographic checksum. Review upstream model and runtime licenses before redistribution or commercialization.

## Object detection

1. The backend decodes the uploaded image and corrects camera rotation when configured.
2. YOLOv8n predicts supported object labels and bounding boxes.
3. The worker retains detections meeting the configured confidence threshold.
4. Each detection records `label`, rounded `score` and `box: [x1, y1, x2, y2]` in image coordinates.
5. Unique labels form the observation's `objects` list.

Examples include person, cell phone, chair, bottle, laptop, remote and book. The exact loaded class list is returned by authenticated `GET /api/status` under `vision.labels`; it is not maintained as a separate hand-written catalogue.

The query parser maps words such as `phone` and `mobile` to the model label `cell phone`. A parser alias alone does not add a detector class. In particular, aliases for keys or glasses do not make reliable key or spectacle detection available.

Object labels do not establish ownership, instance identity or spatial relationships. A phone and chair detected together do not prove that the phone lies under the chair.

## Face enrollment

```mermaid
flowchart LR
    Photo[Uploaded photo or fresh camera frame]
    Detect[YuNet face detection]
    Quality[Exactly one face and minimum face size]
    Align[SFace face alignment]
    Feature[Normalized embedding]
    Pending[Pending sample in SQLite]
    Review[Caretaker review]
    Approved[Approved recognition sample]
    Photo --> Detect --> Quality --> Align --> Feature --> Pending --> Review --> Approved
```

The pipeline resizes the input to `320 x 320` before face detection. Enrollment requires exactly one face. The smaller detected face dimension must be at least 35 pixels in that resized image. The application stores a sample image and its embedding with `approved = false`.

The caretaker must approve the sample before matching can use it. Multiple samples can represent different angles and lighting. Guided enrollment targets six distinct frames within two minutes, but collection can pause while waiting for an acceptable face.

This is embedding-based enrollment. Adding a person does not retrain YuNet, SFace or YOLOv8n from scratch.

## Face recognition

For each detected face:

1. Align the face with OpenCV's SFace recognizer and compute a feature vector.
2. Divide the vector by its L2 norm.
3. Load only approved samples whose person profile has not been deleted.
4. Compute a dot product with each stored normalized sample embedding. This is cosine similarity.
5. Keep the best score for each distinct person.
6. Rank people by those scores.
7. Accept the best identity only when its score meets `face_threshold` and either no competing identity exists or the best score exceeds the runner-up by at least `0.06`.

An accepted result contains the enrolled `id`, `name`, `relationship`, `introduction` and similarity `score`. The relationship comes from the profile, not the image model. Low-confidence or ambiguous faces do not receive an enrolled identity.

Similarity scores are not calibrated probabilities. A score of `0.70` must not be described as a 70% probability that a person is correctly identified.

## Memory retrieval and answers

The application optionally uses Google's Gemini API for natural conversation. The default model is `gemini-3.8-flash`; `gemini-3.5-flash-lite` is selectable for speed. The caretaker saves an API key and enables cloud conversation in Settings. There is no vector database. Face embeddings support identity matching; they are not a semantic memory-search index.

The laptop supplies a bounded text snapshot of enrolled people, latest sightings, active caretaker-approved answers and routines with current progress, plus up to 12 recent messages. Gemini returns a schema-constrained response with an action and optional record IDs. The server validates evidence references and supplies actual Telegram queue results. General questions and varied phrasing are handled by Gemini; personal facts must come from the supplied records. Model instructions discourage invented memories, unsupported current locations and medication-dose advice, but do not guarantee correctness. There is no live web-search tool.

The key is write-only through the settings API and is stored in the local SQLite database, which must remain private. Camera images and face embeddings are not sent to Gemini. Requests use stateless mode (`store=false`). Provider quotas, terms, network availability and charges apply. API timeouts, malformed output, quota/access errors and invalid evidence references produce a visible notice and local fallback.

When AI is disabled or unavailable, the local query handler uses patterns and SQLite records to provide:

- Enrolled-person and relationship introductions
- Last-recorded person or object sightings, including evidence when available
- Recent person identification for `Who is this?`, requiring a camera observation less than 30 seconds old
- Enabled schedules and the next unfinished routine step
- Caretaker-approved exact-question answers with optional expiry
- Help requests with Telegram queue status

The handler searches a bounded recent history rather than all possible lifetime observations: ordinary sighting queries inspect up to 2,000 active events. It can ask for clarification or return `not_found`. Future-visit prediction, unrestricted conversation, automatic personal-object identity and scene reasoning are not implemented.

## Speech components

| Direction | Implementation | Network requirement |
| --- | --- | --- |
| Microphone to text | PyAudio capture, SpeechRecognition and Google speech recognition | Internet for transcription |
| Answer to speaker | Windows SAPI on Windows | No cloud speech API for Windows output |
| Output fallback | pyttsx3 on other platforms | Depends on the installed local speech engine |

The application records and speaks through the laptop. Remote dashboard visitors cannot operate the laptop microphone or speaker through the tunnel. Changing the recognition language does not translate all template responses or guarantee a matching installed speech voice.

## Data handling and evaluation

Managed frames with neither objects nor recognized people are removed after successful inference, unless retained by an enrollment or evidence reference. The latest preview remains available in RAM. Frames that failed inference are not assumed empty.

There is no established accuracy, sensitivity, false-match rate or clinical-benefit figure for this prototype. The workflow test suite checks software behavior rather than real-world model performance.

Before relying on recognition, evaluate it with consented samples across lighting, distance, head poses, occlusion and similar-looking people. Measure false matches and missed matches separately. Test unknown people as well as enrolled people. Keep test images separate from enrollment images and record the threshold used.

The current preprocessing resizes faces directly to a square input. Wide-angle scenes and small faces may lose useful detail. Recognition quality also depends on the ESP32 image quality and the enrollment review. No face liveness or anti-spoofing model is implemented.

For runtime flows and storage, see [ARCHITECTURE.md](ARCHITECTURE.md). For request formats, see [API.md](API.md).
