# SAHAYAK

An ESP32-CAM personal memory assistant with object detection, familiar-face recognition, natural AI conversation, routines and Telegram assistance.

## Current cloud deployment

- Dashboard: https://sahayak-memory-assistant.vercel.app
- Backend: Northflank Developer Sandbox, London, one 512 MB instance with a persistent 6 GB volume. See [cloud deployment and verification](deploy/CLOUD.md).
- The camera uploads directly over verified HTTPS; the laptop backend is not required. Wi-Fi and cloud settings survive power-bank restarts.
- Cloud inference uses OpenCV YOLOv8n ONNX, YuNet and SFace. SQLite and photos remain on the persistent volume. The multi-stage Docker build keeps PyTorch out of the runtime image.
- Cloud voice input/output uses the browser device's microphone and speaker. Local mode retains laptop speech services. No audio hardware is attached to the ESP32.
- Checks covered live uploads, recognition, protected photos, AI replies and restart persistence. One live frame processed in about 929 ms; shared CPU and network conditions affect latency.

References: [Architecture](ARCHITECTURE.md), [API](API.md), [Models](MODELS.md). Credentials, Wi-Fi settings, databases, face photos and model weights are excluded from Git.


## Natural AI conversation

Open **Settings → Ask Sahayak AI**, paste a [Google AI Studio API key](https://aistudio.google.com/apikey), select Gemini Flash (balanced quality/speed) or Flash-Lite (speed), enable AI conversation and save. Use **Test saved AI connection** to verify access and measure one request's latency. Keys stay in the backend's private SQLite settings and are never returned to the dashboard; do not commit that database.

Ask everyday questions naturally and follow up on earlier replies. Gemini receives the question, up to 12 recent chat messages and a limited text snapshot of enrolled people, sightings, approved answers and daily routines. Photos and face embeddings are excluded. Provider terms and charges apply; requests use `store=false`. Chat history resets on reload. AI can make mistakes, has no web search, and cannot establish current location from past sightings. If Gemini is disabled or unavailable, local memory/routine assistance remains available with a visible fallback notice after API failures.

## Optional hosted frontend with laptop backend

The **Start SAHAYAK Online.cmd** desktop launcher runs `start-remote-sahayak.py`. With cloud mode selected in its private configuration, it opens the online dashboard without replacing the cloud API route. In optional laptop/tunnel mode, it starts the laptop backend, creates a temporary Cloudflare tunnel and redeploys the Vercel proxy; keep the laptop and launcher running for that mode. The separate **Start SAHAYAK Backend.cmd** launcher starts local access only.

The temporary tunnel address changes after restarting. Wait for the online launcher to finish redeployment before using the hosted dashboard. An internet connection and the existing Vercel CLI sign-in are required. A permanent domain/tunnel can replace this later.

Models, primary storage and face enrollment remain on the laptop. The frontend deployment contains built UI files and a proxy configuration; it excludes the database, face samples, device token, Wi-Fi credentials and Telegram token. Runtime configuration and deployment metadata live under ignored `.codex_artifacts/`. Data viewed remotely passes through Cloudflare and Vercel. Use the existing caretaker password to sign in. Failed sign-in attempts are rate-limited, and writes require the configured frontend origin.

Laptop microphone and speaker controls remain restricted to the local dashboard, including when a tunnel forwards visitors over loopback. Use `http://localhost:5000/` for laptop voice interaction.

A local personal memory and daily assistance application. The ESP32-CAM sends images over Wi-Fi; the laptop performs object detection, face matching, storage, speech recognition and spoken feedback.

## Start on this laptop

Run `./start-sahayak.ps1` from PowerShell, then open **http://localhost:5000**. The initial screen asks you to create a caretaker password of at least ten characters. No default password is installed. Keep the terminal running. Close it or press Ctrl+C to stop the application.

On this laptop the updated firmware has been compiled and uploaded to **COM7**, after saving a full 4 MB backup of the previous firmware under `.codex_artifacts/backup-before-development`. Live Wi-Fi uploads were confirmed with HTTP 202 responses. Token-free legacy uploads were then disabled. The private `firmware/SahayakCamera/config.h` is configured locally and excluded from source control. To rebuild and upload later, run `./flash-camera.ps1 -Port COM7`; verify the port and Wi-Fi address first.

The current environment uses `C:\Users\tanis\anaconda3\python.exe`. To set up another Python environment:

```powershell
python -m pip install -r sahayak_cloud/requirements.txt
python sahayak_cloud/download_models.py
cd 'Web Interface'
npm.cmd ci
npm.cmd run build
cd ..
python sahayak_cloud/server.py
```

Python 3.11 or 3.12 is recommended for a new local installation. Local Windows voice input needs a microphone, audio output and PyAudio. Current speech interaction uses English. No microphone or speaker is attached to the ESP32.

## Connect the ESP32

USB powers/programs the device. **Image transport is Wi-Fi, not USB serial.** For cloud mode the camera needs internet access to the HTTPS backend. For local mode it must reach TCP port 5000 on the laptop.

The laptop Wi-Fi address observed during development was **192.168.163.157**; verify it with `ipconfig` before flashing. The old firmware pointed to `192.168.1.18`, so update that address if it no longer belongs to this laptop. Network isolation, a stopped server or the Windows firewall can prevent uploads. If Windows asks about Python network access, permit only the trusted private network you intend to use.

For the updated firmware:

1. Open the sketch folder `firmware/SahayakCamera`. Copy `firmware/config.example.h` to `firmware/SahayakCamera/config.h` and fill in Wi-Fi name, password, the laptop server base address and the dashboard's device token. The template contains no Wi-Fi credentials.
2. Use the Espressif Arduino ESP32 board package, select **AI Thinker ESP32-CAM** and the actual USB serial adapter port, then upload using the wiring and programming mode appropriate to your board.
3. Reset into normal operating mode. Open Serial Monitor at 115200 baud. Successful uploads return HTTP **202** (queued for inference).
4. On the dashboard, check that frames arrive and model status is Ready. After the new firmware works, switch off **Allow original firmware without device token** in Settings.

The new firmware sends binary JPEG to reduce memory use; the backend also accepts the original Base64 JSON `/upload` payload. It polls `/api/device-config` every four seconds for capture interval/pause. The original firmware cannot physically pause capture or change interval remotely: server-side pause rejects its incoming frames without processing them. No outage buffer is promised; missed observations are gaps.

Incoming camera frames are rotated 180 degrees on the backend by default to correct an inverted mount. Change Camera orientation in Settings if you remount the camera. Rotation is applied before preview, recognition and saved evidence; manually uploaded enrollment photos and historical evidence are unchanged. Successfully processed frames with neither objects nor recognized people are deleted immediately from managed disk storage unless they are referenced by enrollment samples or saved evidence. The latest camera preview is kept in RAM, so empty frames can still appear in the live view without accumulating image files. Frames whose inference failed are not treated as empty detections.

## Use the application

### Change camera Wi-Fi without reflashing

After installing the firmware with `WifiSetup.h` once, network settings can be changed in the camera's own setup page. The private `config.h` provides first-boot defaults; later web changes are saved in ESP32 NVS and survive power-bank restarts and normal firmware uploads.

While the camera is online, open **Settings → Camera & recognition → Open esp32-cam Wi-Fi setup**. The link appears after a frame arrives from the updated firmware. You can also try **http://sahayak-camera.local/** on a network with mDNS support or use the camera IP printed on Serial Monitor. Sign in with username **caretaker** and the camera's unique setup password. This is separate from the laptop dashboard password.

If the camera cannot connect for **30 seconds**, it opens a Wi-Fi hotspot named **SAHAYAK-Setup-xxxxxx**. Join it using the camera setup password, then open **http://192.168.4.1/** and use the same caretaker login. Your phone may report that this network has no internet; stay connected while saving the settings. Enter the new **2.4 GHz** Wi-Fi name, password and laptop HTTP server address, such as `http://192.168.1.10:5000`. Leave the password blank only to retain it for the same network; use the explicit checkbox for an open network. Save and reconnect your laptop/phone to normal Wi-Fi. The camera restarts and resumes uploads when it can reach the server. The fallback hotspot closes after Wi-Fi has stayed connected for one minute. Camera uploads pause during setup-page activity and resume 30 seconds after the last request, allowing the configuration page to respond promptly.

The setup password is generated once and printed on Serial Monitor at **115200 baud** as `Setup password:`. Keep a private copy; it is retained in NVS. During assisted installation a private copy may be saved under `.codex_artifacts/camera-wifi-setup.json`. Losing the setup password requires USB recovery; no public default or unauthenticated password reset is provided. The page never exposes the saved Wi-Fi password or device token. It uses HTTP on the local network and is intended for trusted networks.

Changing Wi-Fi does not change the enrolled people, memories or Telegram configuration stored on the laptop. The server must remain running, and its LAN IPv4 address must match the address saved on the camera. Do not use `localhost` for the laptop address on the camera. Wi-Fi with client isolation or browser-based sign-in may prevent camera access. The camera does not automatically discover a changed laptop IP.

- **Overview:** latest received frame, connection freshness, people count, saved events and routines.
- **Familiar people:** add name, relationship and an approved introduction. Upload a photo, capture one ESP32 frame, or start guided capture. Guided capture collects up to six single-face samples over two minutes. Slowly vary pose and lighting, then review and approve each sample. Existing `known_faces` images are imported as **pending review**, not automatically activated.
- **Memory timeline:** filter people, objects or rooms; view evidence; correct objects, people or place; confirm a memory or hide it.
- **Ask SAHAYAK:** type or click the microphone; click Stop to cancel capture. Python records through the **laptop microphone**, transcribes with Google, retrieves records and speaks through **laptop speakers** using pyttsx3. Laptop audio endpoints are restricted to localhost. Remote browser access supports typed queries but cannot operate the laptop microphone or speaker.
- **Daily routines:** caretaker-approved steps, explicit Done/Repeat/Help, progress reset and daily progress. In-app due-time prompts run while the dashboard is open; there is no claim of operating-system alarms while it is closed.
- **Care & reassurance:** approved exact-question answers with optional expiry, assistance requests, caretaker acknowledgement and a daily recap limited to confirmed observations and completed routines.
- **Patient view:** larger controls for person introduction, phone search, next activity and help.
- **Settings:** room label, language, retention, capture interval, matching threshold, Telegram and system diagnostics.

## Record a person from the homepage

Use **Record a person**, or press the homepage microphone button and say **“Record a person.”** Keep the same person in the ESP32 view and slowly vary face angle/expression. The laptop rejects dark, blurred and near-duplicate face photos. After eight selected photos (or seven if the 150-second capture times out), it asks **“What name should I give this person?”** Type a name and save, or click **Say the name** and speak only the name to save automatically. Relationship is optional. Saving creates the profile, keeps the photos on the laptop and enables recognition. Cancel removes unfinished captures. This requires the ESP32 to be online and sending fresh frames; the laptop controls voice and microphone. Existing manual photo approval is unchanged.

## Telegram setup

Create a bot with Telegram's BotFather, start the bot from the intended recipient account and enter the bot token and recipient chat ID in Settings. Enable sharing, save, then use the connection test. Status progresses from queued to sent/failed. A help request is not acknowledged merely because Telegram accepted the message: caretaker acknowledgement is a separate action in the dashboard. Selected photos sent through Telegram leave the laptop.

The implementation does not automatically reuse the credentials in old Telegram experiment files. Bot tokens are excluded from API responses and error logs. They are stored in the local SQLite settings, which are protected by the operating system account rather than application-level encryption. Restrict access to the data folder.

## Models and evidence

- **Objects:** existing local `yolov8n.pt`, run through Ultralytics on the laptop. The supported class list appears in Settings. Generic object labels do not establish ownership or distinguish identical phones.
- **Faces:** OpenCV Zoo **YuNet 2023mar** detection and **SFace 2021dec** embeddings. This replaces the unavailable dlib Python dependency in the inspected environment. Enrollment stores normalized embeddings; matching requires an approved sample, a configured cosine-similarity threshold and a separation margin between candidate identities. Similarity scores are not calibrated probabilities. Test the threshold on real camera footage.
- **Conversation and memory retrieval:** optional Gemini conversation grounded in SQLite text records, with local filtering/templates as a fallback. No vector database is required. Personal answers depend on saved evidence; model responses can still be incorrect.

Model sources: https://github.com/opencv/opencv_zoo/tree/main/models/face_detection_yunet and https://github.com/opencv/opencv_zoo/tree/main/models/face_recognition_sface. Retain and review upstream model and Ultralytics licensing before redistribution or commercialization.

The local system identifies past sightings. It does not establish a person's current position, medication ingestion, object ownership or spatial relationships merely from co-occurrence. A fixed room label is useful for a stationary camera; leave it empty for a wearable camera until reliable location inference exists. Existing `Room_1` records are imported with an unconfirmed location.

## Storage and backups

Runtime storage: `sahayak_cloud/data/sahayak.sqlite3`, managed images under `data/images`. SQLite runs in WAL mode. Original JSON memories and original photos remain unchanged. Legacy records are imported once, with a stable identifier to prevent duplication. The original implementation was copied to `.codex_artifacts/backup-before-development` before edits.

Camera-event retention hides old camera events; maintenance removes unreferenced managed photos older than one hour. Legacy images and original reference photos outside `data/images` are not removed. “Hide memory” is a soft hide, not secure erasure. Back up the database and images together with the application stopped. Face profiles, photos and past observations are sensitive personal data.

The initial application supports **one patient profile**, `patient_001`, with one caretaker login. It supports local and cloud deployments. Cloud mode requires HTTPS, preconfigured authentication and persistent storage; see deploy/CLOUD.md. Do not expose an unauthenticated local port 5000 publicly.

## Development and verification

```powershell
python -m pytest tests -q
cd 'Web Interface'
npx.cmd tsc --noEmit -p tsconfig.app.json
npm.cmd run build
# Optional development UI (API proxied to port 5000):
npm.cmd run dev
```

Tests cover access control, invalid uploads, device tokens, person-and-object queries, unknown results, medication uncertainty, expired answers, bounded routine progress, assistance acknowledgement, enrollment approval and protected evidence. Saved-image replay can validate real recognition without claiming live hardware validation. Run a final live camera, microphone and Telegram check with the actual device and recipient before relying on the system.

This is an assistive prototype, not a clinical assessment or proof of patient benefit. Optional future features include tagged personal belongings, reliable room localization, OCR, offline speech, life-story albums and outdoor tracking.

## Enrollment capture and responsiveness

Manual and guided camera enrollment read the latest in-memory preview, including when the empty-frame disk copy has been removed. Guided enrollment attempts the latest frame immediately, collects distinct later frames and reports waiting-for-face, completion and timeout states. The enrollment dialog shows the live preview and quality guidance. While guided collection is active, device configuration requests a one-second capture interval; the existing firmware polls configuration every four seconds. The dashboard refreshes once per second without overlapping refresh batches.

API failures return JSON errors, and the frontend handles non-JSON failures with a readable message. The updated camera firmware uses two PSRAM frame buffers with `CAMERA_GRAB_LATEST` and disables Wi-Fi modem sleep to favour responsiveness; it has been compiled and flashed on COM7. Measured capture rate still depends on Wi-Fi conditions, image size and laptop load.
