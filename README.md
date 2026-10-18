<div align="center">

<a id="top"></a>

<img src="https://img.shields.io/badge/HACK-CMD%20SHIFT%20%2B-9CFFCE?style=for-the-badge&amp;labelColor=111827" alt="Hack CMD SHIFT +" />
<img src="https://img.shields.io/badge/TRACK-Healthcare%20%26%20Wellbeing-91CAFF?style=for-the-badge&amp;labelColor=111827" alt="Healthcare and Wellbeing" />
<img src="https://img.shields.io/badge/STAGE-Assistive%20Prototype-FFCE85?style=for-the-badge&amp;labelColor=111827" alt="Assistive prototype" />

<h1>SAHAYAK</h1>
<h3>Familiar faces. Useful memories. One next step.</h3>

<p>A camera-assisted memory companion for people living with early-stage Alzheimer's disease or mild dementia,<br />with a caretaker connected to everyday assistance.</p>

<a href="https://drive.google.com/file/d/1NvebiTkVziOd6F7CHSi9iMcKMkI8wJ-8/view?usp=sharing"><img src="https://img.shields.io/badge/%E2%96%B6-PROTOTYPE%20DEMO-9CFFCE?style=for-the-badge&amp;labelColor=111827" alt="Open existing prototype demo" /></a>
&nbsp;
<a href="https://sahayak-memory-assistant.vercel.app"><img src="https://img.shields.io/badge/%E2%86%92-LIVE%20DASHBOARD-91CAFF?style=for-the-badge&amp;labelColor=111827" alt="Open deployed SAHAYAK dashboard" /></a>
&nbsp;
<a href="#visual-library"><img src="https://img.shields.io/badge/%E2%96%A7-EXPLORE%20VISUALS-C9B1FF?style=for-the-badge&amp;labelColor=111827" alt="Explore project infographics" /></a>

<br /><br />

[The Idea](#the-idea) · [Experience](#the-experience) · [Architecture](#system-architecture) · [Tech Stack](#technology-stack) · [APIs](#api-reference) · [Get Started](#quick-start) · [Results](#development-and-verification) · [Roadmap](#what-comes-next)

</div>

---

## Current cloud deployment

> **Deployed camera → cloud AI → browser assistance.** The current system runs without a local laptop backend or a temporary tunnel.

| Component | Current deployment |
|---|---|
| **Live dashboard** | [sahayak-memory-assistant.vercel.app](https://sahayak-memory-assistant.vercel.app) — React frontend on Vercel |
| **Backend & inference** | Flask + Waitress on one Northflank x86 service in London |
| **Reported allocation** | Developer Sandbox: 0.2 shared vCPU, 512 MB RAM, one replica |
| **Durable storage** | A 6 GB volume mounted at `/data` for SQLite, photos, settings and approved face samples |
| **Camera transport** | Authenticated binary JPEG uploads directly to Northflank over certificate-verified HTTPS |
| **Voice** | Microphone and spoken answers on the browser device; no audio hardware on the ESP32 |

**Documentation baseline:** comprehensive project report dated **18 October 2026**, source checkpoint [`40ca2e6`](https://github.com/devlopingandroid/Sahayak/commit/40ca2e6). Deployment configuration and results below describe that checkpoint, rather than continuous availability guarantees.

Explore [Architecture](docs/ARCHITECTURE.md), [APIs](docs/API.md), [Models](docs/MODELS.md) and [Cloud deployment](deploy/CLOUD.md). Optional local mode remains available for development and recovery. Credentials, private configurations, databases, face photos, migration archives and model weights stay outside Git.

## The idea

**“Who is this?” · “Where was my phone last seen?” · “What should I do now?”**

SAHAYAK connects these everyday questions to recorded observations and caretaker-approved information. An **ESP32-CAM captures images over Wi-Fi**; the **deployed Northflank backend recognizes supported objects and enrolled people**, saves useful sightings and retrieves the relevant evidence when asked.

The application brings together **visual memory, familiar-person introductions, guided routines, reassurance and acknowledged help requests**. Its purpose is to support recall and coordination; clinical effectiveness has not been established.

### Built for Hack CMD SHIFT +

| Focus | Our approach |
|---|---|
| **Healthcare & Wellbeing** | Assist people with memory difficulties and their caretakers. |
| **A practical prototype** | ESP32-CAM capture, deployed cloud inference and a browser-based interface. |
| **An inspectable answer** | Return the recorded time, available room source and original evidence. |
| **A complete care interaction** | Observe → remember → recall → guide → request human support. |

## The experience

<table>
<tr>
<td width="50%" valign="top">
<h3>👥 Familiar-person introductions</h3>
<p>Capture a person first, then add their name and relationship. The newer workflow targets eight suitable photos; the caretaker can also upload, capture and review profile samples.</p>
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
ESP32-CAM ── verified HTTPS ──► Northflank: Flask + Waitress
  │ POST /upload                  ├─ Bounded frame queue
  │ GET /api/device-config        ├─ YOLOv8n ONNX / OpenCV DNN
  │                               ├─ YuNet + SFace familiar-person matching
  │                               ├─ SQLite + photos on persistent /data
  │                               ├─ Gemini: bounded text conversation
  │                               └─ Telegram notification worker
  │                                              ▲
  └─ Wi-Fi + portable power                      │ HTTPS /api proxy
                                        Vercel: React dashboard
                                                 ▲
                                           Browser device
                                    Text · microphone · spoken replies
```

### Two connected journeys

**Remember:** camera JPEG → authenticated upload → queue → object/face inference → SQLite observation + evidence photo → dashboard and recall.

**Ask:** typed question or browser transcript → `POST /api/query` → saved records and bounded Gemini context → validated answer/action → browser display and optional speech.

The camera sends images **directly to Northflank**. Vercel hosts the UI and proxies browser `/api` requests; it is not the camera-upload destination. The backend does not open the remote user's microphone.

| Where it runs | Responsibility |
|---|---|
| **ESP32-CAM** | Capture fresh JPEGs, authenticate uploads, poll capture configuration and retain Wi-Fi settings in NVS. |
| **Northflank** | Recognition, person enrollment, evidence, memory retrieval, routines, conversation and notifications. |
| **Persistent `/data` volume** | SQLite, managed photos, settings and approved samples/embeddings. Pending queues and previews are not durable. |
| **Vercel** | Publish the frontend and proxy authenticated browser API requests to the backend over HTTPS. |
| **Browser device** | Caretaker and patient views, text input, supported speech recognition and speech synthesis. |
| **External APIs** | Gemini for conversation; Telegram for selected messages/photos; browser-dependent speech services for transcription. |

One backend replica is used because SQLite, in-memory queues and enrollment sessions are designed around a single service. See [cloud deployment](deploy/CLOUD.md) for operation and recovery details.

### Gemini conversation

Gemini receives a question, bounded history and selected **text** records such as relationships, routines and observations. This path does not send raw photos, face embeddings, filesystem paths or secrets. Requests use the Interactions API with `store=false`; this setting is not a statement about every aspect of provider data handling.

The backend validates returned actions and referenced records. Provider failure shows a fallback notice, while structured memory retrieval remains available where the saved evidence supports it. Gemini has no unrestricted SQL or web-search tool in this implementation.

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
| **Camera hardware** | AI Thinker ESP32-CAM | Capture JPEG images and upload over Wi-Fi |
| **Firmware** | Arduino C++, ESP camera driver | Capture, upload, configuration polling and reconnect behavior |
| **Wi-Fi setup** | ESP32 WebServer, DNSServer, Preferences/NVS | Password-protected local provisioning and persistent Wi-Fi/destination settings |
| **Camera TLS** | WiFiClientSecure, bundled trust roots, NTP | Validate HTTPS certificates after clock synchronization |
| **Backend** | Python + Flask | Authenticated APIs, application workflows and memory queries |
| **HTTP server** | Waitress | Serve the deployed Flask application |
| **Object detection** | YOLOv8n ONNX + OpenCV DNN | Detect supported object categories using a static 640-pixel model |
| **Face recognition** | OpenCV YuNet + SFace | Detect faces and compare approved enrolled embeddings |
| **Image processing** | OpenCV + NumPy | Decode, correct orientation, resize and prepare inputs |
| **Storage** | SQLite via Python `sqlite3` + managed JPEG files | Persist structured records and evidence on `/data` |
| **Conversation** | Gemini Interactions API | Natural questions grounded in bounded saved text context |
| **Voice input** | Browser `SpeechRecognition` / `webkitSpeechRecognition` | User-activated transcription where supported |
| **Voice output** | Browser speech synthesis | Read answers aloud and repeat them on the browser device |
| **Frontend** | React + TypeScript + Vite | Caretaker dashboard and patient interface |
| **UI** | Tailwind CSS, shadcn/ui, Framer Motion, Lucide | Components, styling, animation and icons |
| **Notifications** | Telegram Bot API | Selected evidence sharing and help notifications |
| **Hosting** | Vercel + Northflank | Hosted frontend, HTTPS backend and persistent volume |
| **Cloud packaging** | Multi-stage Docker build | Prepare models during build; keep PyTorch out of the inference runtime |

Ultralytics/PyTorch prepare the cloud ONNX model during the build. Deployed inference uses OpenCV DNN. Windows SAPI and laptop microphone services belong to the optional local recovery/development mode.

## API reference

The camera uses device credentials; dashboard operations use caretaker sessions. These are the route families documented in the report; see [docs/API.md](docs/API.md) for route-specific contracts.

| Route or family | Method | Purpose |
|---|---|---|
| `/api/health` | `GET` | Public availability check; model readiness is checked separately through status |
| `/api/auth` | `GET`, `POST` | Authentication state and caretaker sign-in |
| `/api/status` | `GET` | Device freshness, model readiness, counters and recording state |
| `/api/settings` | `GET`, `PATCH` | Read settings and apply validated changes |
| `/upload` | `POST` | Receive authenticated binary JPEG camera frames |
| `/api/device-config` | `GET` | Return capture enablement and interval to the authenticated camera |
| `/api/people` and sample routes | Route-specific | Manage people, relationships and enrollment samples |
| `/api/events` and image routes | Route-specific | Retrieve/manage memories and protected evidence |
| `/api/query` | `POST` | Answer typed or transcribed questions with optional bounded history |
| `/api/routines` and item routes | `GET`, `POST`; item-specific | List/create routines and manage progress/settings |

**Camera request:** `Content-Type: image/jpeg`, `X-Device-Token` and `X-Device-Id`. A `202` response means **queued**, not completed inference; `401` indicates invalid device authentication and `429` a full frame queue. Deployed uploads require authentication; legacy Base64 compatibility is not the normal transport.

**Browser access:** cloud sessions use HttpOnly, SameSite Strict and Secure cookies. Writes require an approved origin, and evidence photos require caretaker authentication. Gemini and Telegram keys are write-only through the settings API. The API does not provide unrestricted permissive CORS.

**Limits:** Flask requests up to 6 MiB; decoded images up to 4 MiB and 16 million pixels. Proxy limits can be lower. The frame queue holds three pending jobs; Telegram uses a separate 30-item notification queue. These limits are not throughput guarantees.

## Quick start

### 1 · Open the deployed dashboard

Visit **[SAHAYAK live dashboard](https://sahayak-memory-assistant.vercel.app)** and sign in with the configured caretaker account. Cloud startup uses existing authentication or explicit private bootstrap configuration; there is no public default password.

You do not need to launch Flask, keep a laptop server running or start a Cloudflare tunnel for the deployed system.

### 2 · Power and check the camera

1. Power the configured ESP32-CAM from USB or a suitable power bank.
2. Keep its saved **2.4 GHz Wi-Fi** connected to the internet.
3. Check the dashboard for a recent preview, fresh device timestamp and ready vision models.
4. Review the room label, orientation, capture interval and capture/pause setting.

USB supplies power/programming; images travel over Wi-Fi. The camera stores its Wi-Fi and cloud destination across restarts. Its direct backend destination is the **Northflank HTTPS endpoint**, not the Vercel website or a laptop LAN address.

### 3 · Try the assistance workflow

Add or review a familiar person, inspect a recent memory, ask a question and open its evidence. On a supported browser, activate the microphone and grant permission, then use repeat-aloud to hear the answer. Typed input remains available. Current conversational output is English; there is no always-listening wake word.

Configure a simple approved routine and demonstrate **Done → next step**, **Repeat** and **Help**. For Telegram, check delivery separately from caretaker acknowledgement.

<details>
<summary><b>👤 Capture first, name afterward</b></summary>

<br />

The newer homepage recording workflow targets **eight** clear, varied face photos. At the 150-second timeout it may accept seven suitable samples. Frames are checked for a single sufficiently large face, exposure, sharpness, variation and consistency before the user provides a name.

The existing profile workflow also supports uploaded/captured samples and the earlier guided collection of up to six photos for review. A complete new recording session was checked locally; a fresh full cloud eight-photo enrollment remains a separate validation item in the report.

</details>

<details>
<summary><b>📶 Change camera Wi-Fi without reflashing</b></summary>

<br />

Use the camera's local setup page from a device on the same reachable network. Where supported, the dashboard setup link or `http://sahayak-camera.local/` opens that page. Sign in with the camera's unique setup password, which is separate from the dashboard password.

If station Wi-Fi is unavailable for 30 seconds, join the password-protected `SAHAYAK-Setup-xxxxxx` recovery hotspot and open `http://192.168.4.1/`. Save the new 2.4 GHz Wi-Fi and the correct HTTPS cloud backend destination. Settings persist in Preferences/NVS.

The setup page uses local HTTP on a trusted network. A public cloud dashboard cannot bypass private-network routing to reach the camera. Keep its setup password privately; USB serial recovery remains available when local access is lost.

</details>

<details>
<summary><b>🛠️ Deploy your own installation or use local recovery</b></summary>

<br />

Start with [deploy/CLOUD.md](deploy/CLOUD.md) for the deployed architecture and [docs/SETUP.md](docs/SETUP.md) for development setup. Clone the project if you are maintaining or deploying it:

```powershell
git clone https://github.com/devlopingandroid/Sahayak.git
cd Sahayak
```

Provision the backend and persistent `/data` volume, configure private authentication/provider settings, deploy the frontend API proxy, then install camera firmware targeting your backend. Keep one backend replica until storage and queue coordination are redesigned. Model preparation belongs to the multi-stage build; private data and credentials must stay out of its context.

For camera programming, use the firmware example configuration and the **AI Thinker ESP32-CAM** board profile. Use your actual serial port, keep private configuration out of Git and monitor upload status at 115200 baud. HTTPS operation requires working NTP and certificate validation.

The former Windows backend, local audio services and temporary tunnel are retained for optional development/recovery. They are not prerequisites for the live cloud installation. Follow the deployment/setup guides for the mode you intend to run.

</details>

## Everyday use

| Screen | What you can do |
|---|---|
| **Overview** | Inspect the latest frame, connection freshness, model state and activity counts. |
| **Familiar people** | Capture-first recording, profiles, relationships, introductions and reviewed enrollment samples. |
| **Memory timeline** | Filter sightings, inspect evidence, correct labels, confirm records or hide them. |
| **Ask SAHAYAK** | Ask by text or supported browser microphone; hear/repeat answers through browser speech synthesis. |
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
<p><sub>Original hardware concept; current recognition runs on Northflank and voice runs on the browser device.</sub></p>

<h4>Recognition pipeline</h4>
<a href="https://raw.githubusercontent.com/devlopingandroid/Sahayak/main/Assets/images/SAHAYAK%20AI%20Recognition%20Pipeline.png"><img src="https://raw.githubusercontent.com/devlopingandroid/Sahayak/main/Assets/images/SAHAYAK%20AI%20Recognition%20Pipeline.png" alt="Recognition pipeline" width="100%" /></a>
<p><sub>Image preparation, supported objects and familiar-person matching.</sub></p>

<h4>From frame to stored record</h4>
<a href="https://raw.githubusercontent.com/devlopingandroid/Sahayak/main/Assets/images/SAHAYAK%20Hardware-to-Software%20Data%20Flow.png"><img src="https://raw.githubusercontent.com/devlopingandroid/Sahayak/main/Assets/images/SAHAYAK%20Hardware-to-Software%20Data%20Flow.png" alt="From frame to stored record" width="100%" /></a>
<p><sub>Conceptual flow; current firmware sends binary JPEG directly to the cloud over authenticated HTTPS.</sub></p>

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

**Recognition describes observations.** YOLO detects supported categories, not ownership of a specific person's belongings. YuNet detects faces; SFace compares approved references. Similarity scores are not calibrated identity probabilities. A last-seen record does not prove current location, a completed action or medication ingestion. Room labels are configured, not measured GPS or indoor positioning.

**Durable cloud memory has a clear boundary.** SQLite, photos, settings and reviewed embeddings live on Northflank's `/data` volume. SQLite uses WAL mode. Back up the database and referenced photos together. Previews, pending frames and active in-memory sessions do not survive restart.

| Destination | Data used by the implemented path |
|---|---|
| **Northflank** | Camera JPEGs, profiles, embeddings, observations, routines and private runtime settings |
| **Vercel** | Frontend requests and proxied API responses, including authorized evidence views |
| **Gemini** | Questions, bounded history and selected text records; no raw photos/embeddings in the conversation path |
| **Speech service** | Audio or recognition-related data according to the browser's selected speech service |
| **Telegram** | Explicitly requested help messages or selected evidence |

**Current controls:** one patient profile and one caretaker login, rate-limited sign-in, protected evidence, device credentials, approved write origins and secure cloud cookies. Camera HTTPS validates certificates. Secrets and private runtime files remain outside Git.

**Current gaps:** SQLite secret values do not have application-level encryption; hiding records is not secure erasure. A complete multi-role account system, formal consent registry, comprehensive audit product and verified secure-deletion workflow are not implemented. Hosting-account and backup access remain important.

The retained infographics are design illustrations. Older labels about local-only processing, microphones on the camera, multiple roles or internet being used only for Telegram do not describe the current deployment. The implementation text and linked documentation describe the current system.

## Development and verification

### Reported engineering results

The following results come from the **18 October 2026 report**. They were not rerun as part of this README update.

| Check | Recorded result | Scope |
|---|---|---|
| **Backend regression suite** | 57 tests passed | Tested workflows, validation, access control, enrollment and cloud behavior |
| **Browser audio tests** | 3 tests passed | Transcript, permission failure, cancellation and repeated listening paths |
| **Frontend** | TypeScript checks and Vite build passed | Compilation and production asset generation |
| **ONNX parity** | 16 saved images | Matching counts/labels; score differences below 0.02 with equal preprocessing |
| **Live camera check** | 37 new cloud frames; no reported inference errors | One hardware verification period |
| **Latest live frame** | About 929 ms inference + 5 ms queue | Single frame; not complete end-to-end transport latency |
| **Cloud saved-image inference** | About 1.6 s; 253 MB peak memory | Separate test process on shared hosting |
| **AI through Vercel** | About 1.6–2.4 s | Successful example replies with the selected Flash-Lite configuration |
| **Restart persistence** | Records, photos and AI configuration checked after restart | Durable data persisted; queues/previews are not durable |
| **Access boundaries** | Protected image returned JPEG when signed in and `401` without authentication; untrusted write origin rejected | Specific recorded access checks |

Network conditions, TLS setup, shared CPU and provider quotas affect timing. These observations are not population recognition accuracy, continuous availability, clinical benefit or a guaranteed response time. Final-device browser voice, a fresh complete cloud eight-photo enrollment, battery runtime, long-duration load and every Telegram delivery case remain separate checks.

### Maintainer checks

With development dependencies installed, the existing workflow includes:

```powershell
python -m pytest tests -q

cd "Web Interface"
npx.cmd tsc --noEmit -p tsconfig.app.json
npm.cmd run build

# Optional frontend development server
npm.cmd run dev
```

See [VALIDATION.md](VALIDATION.md) and [deploy/CLOUD.md](deploy/CLOUD.md) for verification and deployment context. After a release, check health, authenticated model status, recent camera inference, protected evidence and persistence rather than treating an accepted upload as a completed recognition.

Review upstream [Ultralytics](https://github.com/ultralytics/ultralytics) and [OpenCV Zoo](https://github.com/opencv/opencv_zoo) model licenses before redistribution or commercialization.

## What comes next

| Direction | Next work |
|---|---|
| **Recognition evidence** | Evaluate consented, representative images and publish false-match/missed-detection results. |
| **Accessible interaction** | Test patient/caretaker usability, final-device speech, proper-name correction and predictable confirmations. |
| **Privacy & recovery** | Add audited roles, controlled export/deletion, encrypted secret handling and verified backup restoration. |
| **Personal belongings & location** | Evaluate tags, OCR and reliable room localization as separate features with their own evidence. |
| **Cloud operations** | Add observability, load testing and a sustainable hosting plan; shared Sandbox resources and API quotas constrain availability. |

Native mobile support, a physical help button, life-story albums and outdoor tracking remain extensions. The ESP32 installation has no microphone, speaker, GPS or inertial sensor. All-day battery runtime has not been benchmarked.

SAHAYAK is an **assistive prototype**. It does not diagnose dementia, verify medication ingestion, provide validated fall detection or establish an emergency-response service or clinical effectiveness.

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
