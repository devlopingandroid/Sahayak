<div align="center">

<a id="top"></a>

<img src="https://img.shields.io/badge/HACK-CMD%20SHIFT%20%2B-9CFFCE?style=for-the-badge&amp;labelColor=111827" alt="Hack CMD SHIFT +" />
<img src="https://img.shields.io/badge/TRACK-Healthcare%20%26%20Wellbeing-91CAFF?style=for-the-badge&amp;labelColor=111827" alt="Healthcare and Wellbeing" />
<img src="https://img.shields.io/badge/STAGE-Assistive%20Prototype-FFCE85?style=for-the-badge&amp;labelColor=111827" alt="Assistive prototype" />

<h3>Familiar faces. Useful memories. One next step.</h3>

<p>A camera-assisted memory companion for people living with early-stage Alzheimer's disease or mild dementia,<br />with a caretaker connected to everyday assistance.</p>

<a href="https://drive.google.com/file/d/1NvebiTkVziOd6F7CHSi9iMcKMkI8wJ-8/view?usp=sharing"><img src="https://img.shields.io/badge/%E2%96%B6-PROTOTYPE%20DEMO-9CFFCE?style=for-the-badge&amp;labelColor=111827" alt="Open existing prototype demo" /></a>
&nbsp;
<a href="#quick-start"><img src="https://img.shields.io/badge/%E2%86%92-RUN%20LOCALLY-91CAFF?style=for-the-badge&amp;labelColor=111827" alt="Run locally" /></a>
&nbsp;
<a href="#visual-library"><img src="https://img.shields.io/badge/%E2%96%A7-EXPLORE%20VISUALS-C9B1FF?style=for-the-badge&amp;labelColor=111827" alt="Explore project infographics" /></a>

<br /><br />

[The Idea](#the-idea) · [Experience](#the-experience) · [Architecture](#system-architecture) · [Tech Stack](#technology-stack) · [Setup](#quick-start) · [Roadmap](#what-comes-next)

</div>

---

## Current cloud deployment

- Dashboard: https://sahayak-memory-assistant.vercel.app
- Backend: Northflank Developer Sandbox, London, one 512 MB instance with a persistent 6 GB volume. See [cloud deployment and verification](deploy/CLOUD.md).
- The camera uploads directly over verified HTTPS; the laptop backend is not required. Wi-Fi and cloud settings survive power-bank restarts.
- Cloud inference uses OpenCV YOLOv8n ONNX, YuNet and SFace. SQLite and photos remain on the persistent volume. The multi-stage Docker build keeps PyTorch out of the runtime image.
- Cloud voice input/output uses the browser device's microphone and speaker. Local mode retains laptop speech services. No audio hardware is attached to the ESP32.
- Checks covered live uploads, recognition, protected photos, AI replies and restart persistence. One live frame processed in about 929 ms; shared CPU and network conditions affect latency.

References: [Architecture](ARCHITECTURE.md), [API](API.md), [Models](MODELS.md). Credentials, Wi-Fi settings, databases, face photos and model weights are excluded from Git.



## The idea

**“Who is this?” · “Where was my phone last seen?” · “What should I do now?”**

SAHAYAK connects these everyday questions to recorded observations and caretaker-approved information. An **ESP32-CAM captures images over Wi-Fi**; a **cloud backend (or optional laptop server) recognizes supported objects and enrolled people**, saves useful sightings and retrieves the relevant evidence when asked.

The application brings together **visual memory, familiar-person introductions, guided routines, reassurance and acknowledged help requests**. Its purpose is to support recall and coordination; clinical effectiveness has not been established.

### Built for Hack CMD SHIFT +

| Focus | Our approach |
|---|---|
| **Healthcare & Wellbeing** | Assist people with memory difficulties and their caretakers. |
| **A practical prototype** | ESP32-CAM capture, cloud or laptop inference and a browser-based interface. |
| **An inspectable answer** | Return the recorded time, available room source and original evidence. |
| **A complete care interaction** | Observe → remember → recall → guide → request human support. |

## The experience

<table>
<tr>
<td width="50%" valign="top">
<h3>👥 Familiar-person introductions</h3>
<p>Enroll someone with their preferred name, relationship and an approved introduction. Review photo samples before activating recognition.</p>
<blockquote><b>“Who is this?”</b><br />“This is Tanish, your son.”</blockquote>
</td>
<td width="50%" valign="top">
<h3>📸 Recall with evidence</h3>
<p>Search the latest matching sighting and inspect its photo, recorded time and available room label.</p>
<blockquote><b>“Where was the phone last seen?”</b><br />“A phone was last seen by the living room camera at 10:35 AM.”</blockquote>
</td>
</tr>
<tr>
<td width="50%" valign="top">
<h3>🪜 One manageable step</h3>
<p>Caretaker-approved routines offer a single instruction, followed by <b>Done, Repeat or Help</b>. Progress comes from explicit confirmation.</p>
<blockquote><b>“What should I do now?”</b><br />“It is breakfast time. Please go to the dining table.”</blockquote>
</td>
<td width="50%" valign="top">
<h3>🤝 Support that is acknowledged</h3>
<p>Request help, follow its status and receive a separate caretaker acknowledgement. Telegram delivery alone does not mean that someone has responded.</p>
<p>Approved reassurance answers can expire, and the daily recap includes confirmed observations and completed routines.</p>
</td>
</tr>
</table>

<table>
<tr>
<td width="50%" valign="top" align="center">
<h4>The complete experience</h4>
<a href="https://raw.githubusercontent.com/devlopingandroid/Sahayak/main/Assets/images/SAHAYAK%20Complete%20Workflow%20Infographic.png"><img src="https://raw.githubusercontent.com/devlopingandroid/Sahayak/main/Assets/images/SAHAYAK%20Complete%20Workflow%20Infographic.png" alt="The complete experience" width="100%" /></a>
<p><sub>From camera setup to memory recall and daily support.</sub></p>
</td>
<td width="50%" valign="top" align="center">
<h4>A timeline you can revisit</h4>
<a href="https://raw.githubusercontent.com/devlopingandroid/Sahayak/main/Assets/images/SAHAYAK%20Personal%20Memory%20Timeline%20Dashboard.png"><img src="https://raw.githubusercontent.com/devlopingandroid/Sahayak/main/Assets/images/SAHAYAK%20Personal%20Memory%20Timeline%20Dashboard.png" alt="A timeline you can revisit" width="100%" /></a>
<p><sub>Illustrative timeline with people, objects and evidence.</sub></p>
</td>
</tr>
</table>

<p align="center"><sub>Project infographics illustrate the intended experience and data flow. They are design illustrations, not screenshots or measured results. Some diagram labels describe earlier design choices; the implementation notes below describe the current code.</sub></p>

## System architecture

<a href="https://raw.githubusercontent.com/devlopingandroid/Sahayak/main/Assets/images/SAHAYAK%20Memory%20Assistance%20Architecture.png"><img src="https://raw.githubusercontent.com/devlopingandroid/Sahayak/main/Assets/images/SAHAYAK%20Memory%20Assistance%20Architecture.png" alt="SAHAYAK memory assistance architecture" width="100%" /></a>

```text
ESP32-CAM → Wi-Fi upload → Flask / Waitress on laptop
                            ├─ YOLOv8n object detection
                            ├─ YuNet face detection + SFace matching
                            └─ SQLite records + persistent evidence photos
                                         ↓
                         React dashboard / patient view
                            ├─ Natural Gemini conversation and grounded memory queries
                            ├─ Browser speech in cloud mode; laptop SAPI locally
                            └─ Approved Telegram sharing and help alerts
```

**Remote access:** Vercel serves the frontend and proxies API requests to Northflank over HTTPS. The camera uploads directly to Northflank, where models run and a persistent volume holds data. The optional local mode can use a Cloudflare tunnel. See [cloud deployment](deploy/CLOUD.md) and [setup guide](docs/SETUP.md).

| Where it runs | What it does |
|---|---|
| **ESP32-CAM** | Capture and upload; manage Wi-Fi settings and device configuration. |
| **Backend host** | Northflank container or optional laptop: recognition, enrollment, SQLite, evidence, recall, routines and notifications. |
| **Browser** | Caretaker dashboard and patient view. Cloud mode supports typed interaction and browser microphone/speech. |
| **External services** | Gemini conversation, Google speech transcription, Telegram delivery, Vercel and Northflank; optional Cloudflare tunnel. |

Cloud operation does not need the laptop backend. Microphone and speech feedback use the browser device. In local mode, keep the laptop backend running; laptop audio endpoints remain restricted to local access.

## Technology stack

<div align="center">

<img src="https://img.shields.io/badge/ESP32--CAM-111827?style=for-the-badge&amp;logo=espressif&amp;logoColor=9CFFCE" alt="ESP32-CAM" />
<img src="https://img.shields.io/badge/Python-111827?style=for-the-badge&amp;logo=python&amp;logoColor=91CAFF" alt="Python" />
<img src="https://img.shields.io/badge/Flask-111827?style=for-the-badge&amp;logo=flask&amp;logoColor=white" alt="Flask" />
<img src="https://img.shields.io/badge/OpenCV-111827?style=for-the-badge&amp;logo=opencv&amp;logoColor=9CFFCE" alt="OpenCV" />
<img src="https://img.shields.io/badge/React-111827?style=for-the-badge&amp;logo=react&amp;logoColor=91CAFF" alt="React" />
<img src="https://img.shields.io/badge/TypeScript-111827?style=for-the-badge&amp;logo=typescript&amp;logoColor=91CAFF" alt="TypeScript" />
<img src="https://img.shields.io/badge/SQLite-111827?style=for-the-badge&amp;logo=sqlite&amp;logoColor=9CFFCE" alt="SQLite" />
<img src="https://img.shields.io/badge/Telegram-111827?style=for-the-badge&amp;logo=telegram&amp;logoColor=91CAFF" alt="Telegram" />

</div>

<br />

| Layer | Technology | Role |
|---|---|---|
| **Camera hardware** | AI Thinker ESP32-CAM | Image capture and Wi-Fi upload |
| **Firmware** | Arduino C++ | Camera, capture interval, uploads and configuration polling |
| **Wi-Fi setup** | ESP32 WebServer + Preferences/NVS | Browser-based provisioning with persistent settings |
| **Backend** | Python + Flask | APIs, application services and memory queries |
| **HTTP server** | Waitress | Serve Flask on the cloud host or laptop |
| **Objects** | YOLOv8n ONNX/OpenCV (cloud), Ultralytics (local) | Detect supported categories |
| **Faces** | OpenCV YuNet + SFace | Locate faces; compare approved enrolled embeddings |
| **Image processing** | OpenCV + NumPy | Decode, rotate, resize and prepare images |
| **Storage** | SQLite via Python `sqlite3` + local folders | Records, settings and evidence paths; photo files on disk |
| **Voice input** | SpeechRecognition + PyAudio + Google speech | Browser speech recognition in cloud mode; laptop capture locally |
| **Voice output** | Windows SAPI via pywin32 | Browser speech synthesis in cloud mode; SAPI/pyttsx3 locally |
| **Frontend** | React + TypeScript + Vite | Caretaker and patient interfaces |
| **UI** | Tailwind CSS, shadcn/ui, Framer Motion, Lucide | Components, styling, animation and icons |
| **Notifications** | Telegram Bot API | Selected evidence and assistance notifications |
| **Remote access** | Vercel + Northflank | Hosted UI, HTTPS backend and persistent storage; optional local tunnel |
| **Conversation** | Gemini Flash / Flash-Lite | Natural questions grounded in bounded saved text records |

## Quick start

The following instructions describe the optional local installation on a **Windows laptop**, an **ESP32-CAM** and a local network that allows the camera to reach the laptop. Use **Python 3.11 or 3.12**, Node.js/npm and a working microphone/speaker for local voice interaction.

### 1 · Clone and install

```powershell
git clone https://github.com/devlopingandroid/Sahayak.git
cd Sahayak

python -m venv .venv
.\.venv\Scripts\Activate.ps1

python -m pip install -r sahayak_cloud/requirements.txt
python sahayak_cloud/download_models.py

cd "Web Interface"
npm.cmd ci
npm.cmd run build
cd ..
```

The model downloader retrieves the OpenCV face models and YOLOv8n weights. Internet is needed for installation and model downloads.

### 2 · Start the application

```powershell
.\start-sahayak.ps1
```

Open **http://localhost:5000**. On first use, create a caretaker password of at least ten characters; there is no installed default password. Keep the server window running.

### 3 · Connect the camera

1. Copy `firmware/config.example.h` to `firmware/SahayakCamera/config.h`.
2. Set your Wi-Fi details, the HTTPS cloud backend (or laptop LAN address in local mode) and the device token from the dashboard. Keep this file private.
3. In Arduino IDE, select **AI Thinker ESP32-CAM** and your actual serial port. Upload the sketch with the correct programming connections for your board.
4. Open Serial Monitor at **115200 baud**. Successful uploads return **HTTP 202**, meaning the frame was queued for processing.
5. Check the dashboard for fresh frames and ready model status. Disable token-free legacy compatibility after the updated firmware works.

USB supplies power/programming; image transport uses Wi-Fi. Use the laptop's LAN address on the camera, not `localhost`. A fixed camera can use a room label; a wearable camera needs a verified location source before reporting a room.

<details>
<summary><b>📶 Change camera Wi-Fi without reflashing</b></summary>

<br />

With the updated firmware, open **Settings → Camera & recognition → Open esp32-cam Wi-Fi setup**. The setup link becomes available after a frame arrives. The camera also supports `http://sahayak-camera.local/` where mDNS is available.

Sign in as `caretaker` with the camera's unique setup password, printed on Serial Monitor. This is separate from the dashboard password. Settings are stored in NVS and survive restarts.

If the camera cannot connect for 30 seconds, the firmware provides a `SAHAYAK-Setup-xxxxxx` recovery hotspot. Join using its setup password, open `http://192.168.4.1/` and save the new **2.4 GHz Wi-Fi** and reachable laptop server address.

The setup page uses local HTTP and is intended for trusted networks. The camera does not automatically discover a changed laptop IP. Keep a private copy of its generated setup password; losing it requires USB recovery.

</details>

<details>
<summary><b>🌐 Optional hosted frontend</b></summary>

<br />

Follow [deploy/README.md](https://github.com/devlopingandroid/Sahayak/blob/main/deploy/README.md) to configure your Cloudflare client, Vercel project and private remote-access settings. After configuration:

```powershell
python start-remote-sahayak.py
```

The launcher starts the backend if needed, creates a temporary tunnel and updates the Vercel API proxy. Wait for deployment to complete. The temporary address changes after restart, and the laptop, tunnel and server must stay running.

Use `http://localhost:5000/` for laptop voice interaction. Remote browsers support typed queries; remote requests cannot operate the laptop microphone or speaker.

</details>

## Everyday use

| Screen | What you can do |
|---|---|
| **Overview** | Inspect the latest frame, connection freshness, model state and activity counts. |
| **Familiar people** | Add profiles; upload, capture or collect guided samples; review and approve them. |
| **Memory timeline** | Filter sightings, inspect evidence, correct labels, confirm records or hide them. |
| **Ask SAHAYAK** | Search by text; use the laptop microphone and speaker locally. |
| **Daily routines** | Configure steps and record Done, Repeat or Help actions. |
| **Care & reassurance** | Manage approved answers, expiry, assistance acknowledgement and a confirmed daily recap. |
| **Patient view** | Use larger controls for introductions, object recall, next activity and help. |
| **Settings** | Manage rooms, capture/pause, orientation, thresholds, retention, Telegram and diagnostics. |

For Telegram, create a bot with BotFather, start it from the intended recipient account and configure the token/chat ID in Settings. Enable sharing and run the connection test. **Queued → sent/failed** tracks delivery; caretaker acknowledgement is a separate dashboard action.

## Visual library

All 14 project infographics below come from this repository's [`Assets/images`](https://github.com/devlopingandroid/Sahayak/tree/main/Assets/images). Click an image to read it at full size. Illustrations describe the project design; implementation details and limitations are stated in the text.

<details>
<summary><b>🔎 Capture and recognition</b></summary>

<br />

<h4>Hardware setup</h4>
<a href="https://raw.githubusercontent.com/devlopingandroid/Sahayak/main/Assets/images/SAHAYAK%20Hardware%20Setup%20Infographic.png"><img src="https://raw.githubusercontent.com/devlopingandroid/Sahayak/main/Assets/images/SAHAYAK%20Hardware%20Setup%20Infographic.png" alt="Hardware setup" width="100%" /></a>
<p><sub>Camera, Wi-Fi and the laptop processing environment.</sub></p>

<h4>Recognition pipeline</h4>
<a href="https://raw.githubusercontent.com/devlopingandroid/Sahayak/main/Assets/images/SAHAYAK%20AI%20Recognition%20Pipeline.png"><img src="https://raw.githubusercontent.com/devlopingandroid/Sahayak/main/Assets/images/SAHAYAK%20AI%20Recognition%20Pipeline.png" alt="Recognition pipeline" width="100%" /></a>
<p><sub>Image preparation, supported objects and familiar-person matching.</sub></p>

<h4>From frame to stored record</h4>
<a href="https://raw.githubusercontent.com/devlopingandroid/Sahayak/main/Assets/images/SAHAYAK%20Hardware-to-Software%20Data%20Flow.png"><img src="https://raw.githubusercontent.com/devlopingandroid/Sahayak/main/Assets/images/SAHAYAK%20Hardware-to-Software%20Data%20Flow.png" alt="From frame to stored record" width="100%" /></a>
<p><sub>Conceptual flow; current firmware uses binary JPEG, with legacy Base64 support.</sub></p>

</details>

<br />

<details>
<summary><b>💬 Recall, routines and Telegram</b></summary>

<br />

<h4>Personal memory recall</h4>
<a href="https://raw.githubusercontent.com/devlopingandroid/Sahayak/main/Assets/images/SAHAYAK%20Personal%20Memory%20Recall%20Flow.png"><img src="https://raw.githubusercontent.com/devlopingandroid/Sahayak/main/Assets/images/SAHAYAK%20Personal%20Memory%20Recall%20Flow.png" alt="Personal memory recall" width="100%" /></a>
<p><sub>Retrieve a recorded sighting with evidence and uncertainty.</sub></p>

<h4>Daily assistance</h4>
<a href="https://raw.githubusercontent.com/devlopingandroid/Sahayak/main/Assets/images/SAHAYAK%20Daily%20Assistance%20Workflow.png"><img src="https://raw.githubusercontent.com/devlopingandroid/Sahayak/main/Assets/images/SAHAYAK%20Daily%20Assistance%20Workflow.png" alt="Daily assistance" width="100%" /></a>
<p><sub>Approved steps, explicit completion and help.</sub></p>

<h4>Telegram notification flow</h4>
<a href="https://raw.githubusercontent.com/devlopingandroid/Sahayak/main/Assets/images/SAHAYAK%20Telegram%20Notification%20Flow.png"><img src="https://raw.githubusercontent.com/devlopingandroid/Sahayak/main/Assets/images/SAHAYAK%20Telegram%20Notification%20Flow.png" alt="Telegram notification flow" width="100%" /></a>
<p><sub>Selected evidence delivery and assistance messages.</sub></p>

</details>

<br />

<details>
<summary><b>🗃️ Data and privacy</b></summary>

<br />

<h4>Database design illustration</h4>
<a href="https://raw.githubusercontent.com/devlopingandroid/Sahayak/main/Assets/images/SAHAYAK%20SQLite%20Database%20Schema%20Infographic.png"><img src="https://raw.githubusercontent.com/devlopingandroid/Sahayak/main/Assets/images/SAHAYAK%20SQLite%20Database%20Schema%20Infographic.png" alt="Database design illustration" width="100%" /></a>
<p><sub>Conceptual entity map; store.py defines the actual schema.</sub></p>

<h4>Privacy design overview</h4>
<a href="https://raw.githubusercontent.com/devlopingandroid/Sahayak/main/Assets/images/SAHAYAK%20Privacy%20and%20Security%20Overview.png"><img src="https://raw.githubusercontent.com/devlopingandroid/Sahayak/main/Assets/images/SAHAYAK%20Privacy%20and%20Security%20Overview.png" alt="Privacy design overview" width="100%" /></a>
<p><sub>Illustration; read the current implementation notes below for exact controls.</sub></p>

</details>

<br />

<details>
<summary><b>🧭 Monitoring and roadmap</b></summary>

<br />

<h4>Monitoring and support</h4>
<a href="https://raw.githubusercontent.com/devlopingandroid/Sahayak/main/Assets/images/SAHAYAK%20Real-Time%20Care%20Monitoring%20Flow-3.png"><img src="https://raw.githubusercontent.com/devlopingandroid/Sahayak/main/Assets/images/SAHAYAK%20Real-Time%20Care%20Monitoring%20Flow-3.png" alt="Monitoring and support" width="100%" /></a>
<p><sub>Illustrative monitoring flow; current alerts do not establish fall or clinical-event detection.</sub></p>

<h4>Implementation roadmap illustration</h4>
<a href="https://raw.githubusercontent.com/devlopingandroid/Sahayak/main/Assets/images/SAHAYAK%20Implementation%20Roadmap%20Infographic.png"><img src="https://raw.githubusercontent.com/devlopingandroid/Sahayak/main/Assets/images/SAHAYAK%20Implementation%20Roadmap%20Infographic.png" alt="Implementation roadmap illustration" width="100%" /></a>
<p><sub>Design milestones; source and validation notes establish current status.</sub></p>

<h4>Alternative timeline illustration</h4>
<a href="https://raw.githubusercontent.com/devlopingandroid/Sahayak/main/Assets/images/SAHAYAK%20Personal%20Memory%20Timeline%20Dashboard%20%281%29.png"><img src="https://raw.githubusercontent.com/devlopingandroid/Sahayak/main/Assets/images/SAHAYAK%20Personal%20Memory%20Timeline%20Dashboard%20%281%29.png" alt="Alternative timeline illustration" width="100%" /></a>
<p><sub>A second visual reference for the memory experience.</sub></p>

</details>

<br />


## Memory, privacy and trust

**Recognition answers a limited question.** YOLO identifies supported categories; it does not prove that a phone belongs to a particular person. YuNet detects faces, and SFace compares approved references. Similarity scores are not calibrated identity probabilities. A last-seen event does not establish current position, an action or medication ingestion.

**Storage follows deployment mode.** Cloud records and photos live on the persistent Northflank `/data` volume. Local mode uses `sahayak_cloud/data/sahayak.sqlite3` and `data/images`. SQLite uses WAL mode. Back up the database and photos together; do not commit either.

**External services remain visible.** Google speech processes voice externally; Telegram receives selected information; cloud access carries data through Northflank and Vercel; the optional local tunnel also uses Cloudflare. The system is not fully offline. Cloud speech uses browser APIs; local Windows speech uses installed SAPI voices. The current interface uses English.

**Controls reflect the current prototype.** There is one patient profile and one caretaker login. Evidence requires authenticated access, camera uploads use device credentials, and settings control capture and sharing. Telegram settings live in the private backend database; database values do not have application-level encryption. Hiding a memory is not secure erasure.

Some privacy infographic labels describe intended controls rather than current implementation—for example, multiple roles, environment-variable token storage or internet being used only for Telegram. The notes above take precedence.

## Development and verification

```powershell
python -m pytest tests -q

cd "Web Interface"
npx.cmd tsc --noEmit -p tsconfig.app.json
npm.cmd run build

# Optional frontend development server
npm.cmd run dev
```

See [VALIDATION.md](https://github.com/devlopingandroid/Sahayak/blob/main/VALIDATION.md) for the project's existing verification record and remaining hardware/user checks. Reproduce checks in your own environment; a saved-image replay or model benchmark is not a measurement of live patient benefit.

Review upstream [Ultralytics](https://github.com/ultralytics/ultralytics) and [OpenCV Zoo](https://github.com/opencv/opencv_zoo) model licenses before redistribution or commercialization.

## What comes next

| Direction | Next engineering question |
|---|---|
| **Personal belongings** | How can reviewed references or tags distinguish one person's item from a generic category? |
| **Location** | How can wearable room or outdoor location be established reliably? |
| **Voice access** | How can offline speech and browser-side voice expand access? |
| **Usability** | Which interactions work well for patients and caretakers in structured evaluation? |
| **Deployment** | How should permanent remote access, operational controls and multiple profiles be introduced? |

OCR, native mobile support, a physical help button, life-story albums and outdoor tracking remain extensions. The current prototype does not diagnose dementia, verify medication ingestion or establish clinical effectiveness.

---

<div align="center">

<b>SAHAYAK</b><br />
Personal memory. Practical assistance. A caretaker in the loop.

<br /><br />

Built for <b>Hack CMD SHIFT +</b> · Healthcare &amp; Wellbeing

<br /><br />

[Back to top ↑](#top)

<img src="https://capsule-render.vercel.app/api?type=waving&amp;color=0:0B1220,45:164E63,100:6EE7B7&amp;height=120&amp;section=footer" alt="SAHAYAK footer" width="100%" />

</div>
