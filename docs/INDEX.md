# SAHAYAK documentation

Camera-assisted personal memory and daily assistance, built for **Hack CMD SHIFT + · Healthcare & Wellbeing**.

## Start reviewing

| Your question | Read |
|---|---|
| What does the project do? | [Project overview](../README.md) |
| How can I evaluate it in three minutes? | [Demo walkthrough](DEMO.md) |
| Where does each component run? | [System architecture](ARCHITECTURE.md) |
| Which routes connect the camera and dashboard? | [API reference](API.md) |
| What do the vision models actually identify? | [Models and inference](MODELS.md) |
| What has been checked, and what remains pending? | [Current validation summary](VALIDATION.md) |
| How is the cloud deployment operated? | [Cloud deployment](../deploy/CLOUD.md) |
| How do I develop or recover locally? | [Setup](SETUP.md) |
| What is planned next? | [Roadmap](ROADMAP.md) |

## Repository map

```text
Sahayak/
├── README.md                  Project entry point and live/demo links
├── LICENSE                    Licensing status and upstream references
├── .github/workflows/ci.yml    Backend and frontend checks
├── docs/                      Architecture, APIs, models, demo and evidence
├── Assets/images/             Existing 14 project infographics
├── Assets/screenshots/        Reserved for future approved captures
├── firmware/                  ESP32-CAM capture and Wi-Fi provisioning
├── sahayak_cloud/             Flask services, vision, storage and conversation
├── Web Interface/             React/TypeScript frontend
├── deploy/                    Cloud packaging, migration and configuration
├── scripts/diagnostics/       Optional manual microphone diagnostic
├── tests/                     Backend regression tests
└── Dockerfile                 Cloud backend image
```

The existing root launchers, `test.py`, `package-lock.json` and `VALIDATION.md` remain at their original paths for compatibility. The root validation file preserves historical local checks; the current dated summary is here in `docs/`.

## Current operating path

ESP32-CAM → authenticated HTTPS → Northflank inference and `/data` storage → Vercel API proxy → browser dashboard. Browser speech runs on the browser device. Optional local mode is documented separately from the current cloud path.

The baseline engineering report is dated **18 October 2026**, implementation checkpoint [`40ca2e6`](https://github.com/devlopingandroid/Sahayak/commit/40ca2e6). See the validation summary for the distinction between reported measurements and later repository checks.
