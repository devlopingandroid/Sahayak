# Maintenance scripts

## Optional diagnostic

`diagnostics/microphone_check.py` is a byte-identical compatibility copy of the existing root `test.py`. It manually opens a local microphone and sends a transcript request to the configured Google speech recognition service. It is not part of the automated regression suite and is not needed for cloud browser voice.

Its original hardcoded microphone index is retained. Review the index for your development device before intentionally running it. The original root script remains available at its existing path.

## Existing entry points

The root `start-sahayak.ps1`, `start-remote-sahayak.py` and `flash-camera.ps1` retain their original locations. Deployment and launcher references are unchanged by the submission structure update.
