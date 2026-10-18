# Validation and evidence

## Evidence baseline

The comprehensive project report dated **18 October 2026** describes source checkpoint [`40ca2e6`](https://github.com/devlopingandroid/Sahayak/commit/40ca2e6). The table below summarizes that report and the [cloud verification record](../deploy/CLOUD.md). It is a dated engineering record, not a claim of continuous availability.

| Check | Reported result | Interpretation |
|---|---|---|
| Backend regression suite | 57 tests passed | Tested workflows, access boundaries, enrollment and cloud behavior. |
| Browser audio tests | 3 tests passed | Transcript, permission failure, cancellation and repeated listening paths. |
| Frontend | TypeScript check and Vite build passed | Frontend compilation and production assets. |
| ONNX parity | 16 saved images | Matching counts/labels and score differences below 0.02 under equal preprocessing. |
| Cloud camera verification | 37 newly processed frames without reported inference errors | One hardware check, not a long-duration load study. |
| Latest live frame | Approximately 929 ms inference + 5 ms queue | Single observation, excluding complete camera transport. |
| Separate saved-image cloud process | Approximately 1.6 s inference; 253 MB peak memory | Different test from the live frame measurement. |
| AI replies through Vercel | Approximately 1.6–2.4 s | Successful examples; provider availability and quotas affect replies. |
| Cloud restart | Records, evidence and AI configuration retained | Persistent `/data`; pending queues and previews remain in memory. |
| Protected image access | JPEG when authenticated; 401 without session | Specific recorded authentication check. |
| Untrusted write origin | Rejected | Specific recorded origin validation check. |

The [original root validation log](../VALIDATION.md) preserves the earlier 17 October local checks and their incremental counts. Those entries are historical; they do not supersede the dated cloud summary above.

## Reproduce automated checks

Use a disposable development environment. Backend regression tests use temporary stores and test doubles rather than the production database, real patient photographs, live Gemini calls or actual Telegram delivery.

```sh
python -m pip install -r tests/requirements-ci.txt
python -m pytest tests -q
```

From `Web Interface/`:

```sh
npm ci
node --test tests/browser-audio.test.cjs
npx tsc --noEmit -p tsconfig.app.json
npm run build
```

The [CI workflow](../.github/workflows/ci.yml) runs these backend and frontend checks for relevant pushes and pull requests. It can also be run manually from Actions. It does not deploy, flash firmware, migrate private data or exercise a live camera. A green run is evidence only for the checks included in that run.

## Repository structure check — 18 October 2026

The submission structure was checked in an isolated Windows checkout, with Python 3.12 and a disposable test environment. The existing 57 backend tests passed after installing the speech-recognition package needed by a mocked audio regression test. That dependency is included in the new `tests/requirements-ci.txt`; production requirements are unchanged. All three browser-audio tests, the TypeScript check and the Vite production build also passed.

All 80 previously tracked files remain at their original paths. Only README/navigation notices were inserted into three existing Markdown files; original content is retained. Application code, firmware, deployment configuration, model references and original assets are unchanged. No site screenshots are included. Hosted CI results are available through the Actions page separately from these local checks.

## Pending evaluation

- Fresh complete cloud eight-photo enrollment.
- Browser microphone and audible playback on the final demonstration device.
- Every Telegram delivery/failure and human acknowledgement scenario.
- Battery runtime, enclosure temperature and long-duration cloud load.
- Representative face/object evaluation with false matches and missed detections.
- Patient/caretaker usability and clinical outcomes.

Counts and timing examples do not establish population accuracy, medical benefit or a guaranteed service latency. Room labels are configured; generic object categories do not prove ownership.
