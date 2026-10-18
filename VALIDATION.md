> **Historical local validation log.** Original entries below are retained. Read [docs/VALIDATION.md](docs/VALIDATION.md) for the dated cloud summary and current check commands.

# Local verification

Verified on 17 October 2026 on the connected Windows laptop.

## Passed

- React/Vite production build and TypeScript checking.
- 12 backend workflow tests: authentication/origin checks, token-required image upload, invalid images, combined person/object retrieval, missing sightings, medication uncertainty, expired answers, routine completion limits, changed-step confirmation reset, help acknowledgement, enrollment review, protected evidence, recap filtering and preservation of caretaker-confirmed observations.
- Browser workflows for sign-in, routine creation/progress, face sample approval, timeline filtering and an evidence-grounded phone query.
- Desktop and phone-sized patient view inspection; no horizontal overflow in the tested phone viewport; no browser errors reported in the test session.
- YOLOv8n and OpenCV YuNet/SFace model loading on the laptop.
- Saved-image replay in a separate test instance: Tanish identified from an approved reference, object label detected, event persisted and evidence image served successfully.
- Default laptop microphone available; synthetic spoken question transcribed successfully through the configured Google speech service. Speaker service initialized without errors.
- ESP32 firmware compiled for `esp32:esp32:esp32cam` with Arduino ESP32 core 2.0.14. Program size 979673 bytes, global RAM 50424 bytes.
- Previous 4 MB flash image backed up before writing new firmware. New firmware uploaded to COM7 with successful flash hash verification.
- Real ESP32-CAM binary JPEG uploads received over Wi-Fi with HTTP 202, including consecutive uploads after disabling token-free legacy compatibility.
- A live camera frame produced a `person` detection and a saved camera memory. No name was assigned because reference samples remain unapproved in the real installation.
- 139 legacy memories imported without overwriting original files; 14 existing reference photos made available for caretaker approval.

## User configuration and remaining checks

- Create a caretaker password at http://localhost:5000. No default caretaker password was installed.
- Review and approve the appropriate face samples; add relationship and approved introduction. Real camera identification accuracy must be evaluated after enrollment.
- Enter Telegram bot token and recipient chat ID, enable sharing and send a connection test. Real Telegram delivery has not been tested without these credentials.
- Try a spoken question through the laptop microphone. Synthetic speech recognition and device availability checks do not establish real-user speech performance.
- The app supports one patient profile on a private LAN. The planned optional personal-object identification, reliable wearable room localization, native mobile application and physical help button are not implemented.

The original application source and firmware backup are under `.codex_artifacts/backup-before-development`. The runtime database and managed evidence are under `sahayak_cloud/data`. Private Wi-Fi configuration is excluded from source control.

## Camera cleanup and orientation update

- 15 backend tests passed after adding 180-degree camera-upload rotation and immediate empty-frame deletion. Tests verify that disk cleanup preserves saved evidence and pending enrollment samples, protects files outside managed storage, keeps a RAM-backed preview available, and supports disabling rotation.
- Frontend TypeScript and production build checks passed. The running server was restarted; live uploads continued without inference errors and empty-frame disk references were cleared.

## Enrollment regression fix

- 19 backend tests passed, including enrollment after empty-frame disk deletion, immediate guided capture from RAM, fast enrollment interval, quality feedback and JSON server errors.
- TypeScript, production build and frontend error-response checks passed.
- Real-model replay in an isolated instance: manual enrollment returned HTTP 201 with a null device disk reference; guided enrollment reached six samples. The browser single-frame button also saved a sample successfully.
- Updated freshness/power-saving firmware compiled and was uploaded to COM7 with flash hashes verified.

## Wi-Fi setup page — 17 October 2026

- 27 backend workflow tests pass, including camera setup links derived from private client addresses and rejection of public/forwarded-address links. Frontend TypeScript and Vite production build pass.
- ESP32-CAM firmware with WebServer, Preferences, DNS and mDNS support compiles. The setup responsiveness update uses 1,053,713 bytes of program storage (33%) and 53,296 bytes of global RAM (16%). Initial setup firmware was flashed on COM7 with flash hashes verified.
- Live camera uploads resumed with HTTP 202 after flashing. The authenticated setup page is reachable over the current LAN.
- Hardware HTTP checks passed for unauthenticated access (401), authenticated form access, saved-password non-disclosure, form nonce enforcement (403), rejection of public/localhost/invalid-port server destinations, and rejection of short Wi-Fi passwords (400). Validation requests did not change the network.
- The firmware provides an automatic recovery access point after 30 seconds without a station connection. A deliberate Wi-Fi outage/hotspot-join test has not been performed; current checks retain the user's working network.
- The camera's private setup credentials and instructions are saved under `.codex_artifacts/Camera Wi-Fi Setup.txt`; they are not included in dashboard API responses or validation output.
- Existing settings were saved through the form and later read back after a USB reset, confirming persistence of network settings and setup credentials. After the responsiveness firmware was installed and flash hashes verified, another form save returned HTTP 200 and fresh camera uploads were observed after the automatic restart. A follow-up portal GET timed out on the current Wi-Fi; initial page requests can still be slow while camera/network operations are active. An actual move to a different Wi-Fi network and recovery-hotspot join remain untested.
