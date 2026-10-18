# Free cloud backend deployment

Deployed target: **Northflank Developer Sandbox**, London, service `sahayak-backend` in project `default`, 0.2 shared vCPU / 512 MB, one instance. The attached 6 GB `sahayak-data` volume at `/data` is marked Free in the console. Delhi and Singapore require a paid upgrade. Keep the account and project on the free plan; do not upgrade or provision paid resources.

Northflank advertises two always-on free services and one free database, but calls this a testing plan, not production hosting. Free quotas and shared CPU prevent a guarantee of uninterrupted service or localhost-equivalent latency. Official details: https://northflank.com/pricing and https://northflank.com/docs/v1/application/billing/pricing-on-northflank . Account and card verification are complete. Oracle signup was abandoned at the user's request.

## Live endpoints and verification (18 October 2026)

- Frontend: https://sahayak-memory-assistant.vercel.app
- Backend: https://http--sahayak-backend--zptn6fs9b2zg.code.run
- Vercel proxies `/api/:path*` to the backend over HTTPS. It no longer needs the laptop tunnel.
- Imported snapshot: 5 total profiles (4 active), 43 samples, 353 memory events, 2 routines, 285 photos. Local source files and data were preserved. Records and AI configuration survived a cloud service restart.
- Cloud object/face inference on an existing enrolled photo succeeded, recognizing the enrolled person and objects, with about 1.6 seconds inference and 253 MB peak memory in that separate test process. This is a sample measurement, not a latency guarantee.
- Direct warm API requests measured about 200-290 ms. Through Vercel, profile/status/routine requests measured about 0.5-0.85 seconds. First connections can take longer.
- Gemini 3.8 Flash returned an upstream high-demand 503, so cloud settings now select the existing Gemini 3.5 Flash-Lite option. Live grounded schedule and general chat requests through Vercel returned Gemini answers in about 1.6-2.4 seconds.
- Protected photo delivery succeeded with authentication and returned 401 without it. Untrusted write origins were rejected. All recognition models report ready.
- The existing camera certificate roots successfully validated the backend TLS chain.
- Northflank startup, readiness and liveness HTTP probes check `/api/health` on port 5000. Vision readiness is checked separately through authenticated `/api/status`; the public probe only checks server availability.
- **Hardware cutover verified:** HTTPS firmware was compiled and flashed successfully over COM7. Saved Wi-Fi was preserved, and the new compiled cloud destination was applied to NVS once. After boot the camera uploaded JPEGs with HTTP 202; the cloud received and processed 37 new frames during verification with no errors. The latest measured inference was 929 ms and queue time 5 ms. The authenticated Vercel live image endpoint returned JPEG data. No local backend was listening on port 5000 during the final camera check. The camera can return to power-bank power while retaining Wi-Fi and cloud settings. A new eight-photo enrollment session was not run during this migration check.
- Browser microphone and speech paths are included in the deployed frontend. Their real-device operation still needs a signed-in browser check with microphone permission.
- `start-remote-sahayak.py` now checks private deployment config for cloud mode and opens the online dashboard instead of replacing the Vercel route with a laptop tunnel.

## Northflank configuration

Build the root `Dockerfile` as a combined service, single instance, `nf-compute-20` (512 MB / 0.2 shared vCPU). The multi-stage build exports YOLOv8n to static 640-pixel ONNX and generates the 80 class labels; PyTorch is only installed in the build stage. The runtime keeps object detection and face recognition using OpenCV without PyTorch or Ultralytics imports.

Attach a persistent volume at `/data` before migrating the database/photos. Verify the final free quota and ownership for UID 1000; an ephemeral directory is not acceptable. The deployed 6 GB volume is marked Free. Configure runtime variables from `cloud.env.example` using private provider secrets. Expose container port 5000 through the provider's HTTPS proxy. Caddy and `compose.cloud.yaml` are only for a self-managed VM and are not used on Northflank.

This installation built from a source-only tar bundle without pushing GitHub changes. For a rebuild, provide a fresh reachable source bundle URL; the temporary transfer tunnel used for initial deployment is stopped after transfer. The bundle contains only Dockerfile, backend source and build scripts. Private migration archives must never be served publicly: the transfer used a separate bearer-authenticated route, TLS and a SHA-256 integrity check. The migration container ran `sleep infinity` while importing, then its command was restored to the image default before application startup.

Local validation: 57 backend tests pass. On 16 existing images the OpenCV ONNX detector matched PyTorch detection counts and labels, with confidence differences under 0.02, when both used the same static square preprocessing. Average object inference was about 220 ms on the development laptop; this does not measure the provider's much smaller CPU. A blank-frame check with all three models loaded used about 150 MB RSS on Windows. The complete Linux container still needs build, peak-memory and latency validation on the actual free host.

## What is ready

- `Dockerfile` builds a CPU-only Python backend with YOLOv8n and OpenCV face models. No patient data or local credentials are copied into the image.
- `compose.cloud.yaml` runs one backend with persistent `/data` storage and Caddy HTTPS. It restarts after a host reboot. Keep one replica: SQLite, camera queues and capture state are designed for one process.
- Cloud mode disables server microphone/speaker access, requires a preconfigured caretaker login, enables secure session cookies and rejects legacy unauthenticated camera uploads.
- The frontend uses browser speech recognition and speech synthesis when the backend reports cloud mode. Use Chrome/Edge over HTTPS and allow microphone access. Existing laptop mode keeps laptop audio.
- Cloud inference uses one OpenCV CPU thread and warms YOLO ONNX during startup. Models stay loaded. Camera firmware verifies HTTPS with ISRG X1/X2 roots, synchronizes time with NTP and reuses HTTP/TLS connections. Check the provider's certificate chain before installing firmware.

## Private migration

Run from the project root:

```powershell
python deploy/export_cloud_data.py --source sahayak_cloud/data --output .codex_artifacts/sahayak-private-cloud-migration.tar.gz
```

The archive contains a consistent SQLite snapshot and referenced photos, including saved credentials and enrollment embeddings. It remaps Windows image paths to `/data/images`. **Transfer it only through a private authenticated connection to the backend's persistent volume; never include it in Git, a public container image or Vercel.** The original database and photos are preserved. Generate a fresh archive immediately before the final cutover so it includes the latest records.

For a self-managed VM alternative, copy the source-only deployment package and private migration archive using SSH. Create `deploy/cloud-data`, extract the archive there, and set ownership to UID 1000 with directory permissions 700 and file permissions 600. Do not publish port 5000 directly. Allow SSH from the caretaker's IP; allow ports 80/443 for Caddy and device traffic. Keep public access controlled by the existing caretaker session and device token.

## HTTPS and startup

Copy `cloud.env.example` to private `cloud.env`; set `SAHAYAK_ALLOWED_ORIGINS` to the existing Vercel URL. The migrated database supplies the existing login, device token, Gemini API key and Telegram configuration. For a new installation use the three documented bootstrap environment variables instead; remote first-user setup is disabled.

Use a hostname you control pointing to the VM's public IP. If none is available, a hostname from an appropriate free DNS service can be used after verifying its DNS resolution and certificate issuance. Do not switch the ESP32 to an unverified hostname or disable certificate validation.

On the VM, from `deploy/`:

```sh
BACKEND_HOST=your-verified-hostname docker compose -f compose.cloud.yaml up -d --build
```

Caddy obtains and renews HTTPS certificates. Its certificate chain must match the camera trust roots. Confirm `/api/health`, authenticate, wait for vision readiness, and check secure sessions, protected photos, query output, routine progress and restart persistence.

## Vercel and camera cutover

Update the Vercel deployment's `/api/:path*` rewrite to `https://YOUR_BACKEND/api/:path*`. Deploy only the frontend build and rewrite configuration. The laptop's temporary tunnel is no longer part of the cloud route.

Compile and install the updated camera firmware over USB. A newly compiled HTTPS destination is applied once while retaining saved Wi-Fi; later setup-page edits remain authoritative until another cloud destination is installed. The setup page accepts HTTPS cloud hostnames and retains private HTTP LAN addresses for laptop mode. Its existing device token must match the migrated backend. A working NTP connection is required for certificate checks. Keep local firmware/config and data backups until cloud upload, recognition, enrollment, Gemini, Telegram and browser speech are verified.

Measure cloud HTTP round trips, frame queue/inference time, and Gemini response time separately. Verify the system with the laptop backend stopped before claiming laptop-independent operation. No Vercel production rewrite or camera address should be changed until the cloud endpoint passes these checks.
