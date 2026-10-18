# Three-minute SAHAYAK walkthrough

**Track:** Hack CMD SHIFT + · Healthcare & Wellbeing

- [Live cloud dashboard](https://sahayak-memory-assistant.vercel.app)
- [Existing prototype demo video](https://drive.google.com/file/d/1NvebiTkVziOd6F7CHSi9iMcKMkI8wJ-8/view?usp=sharing)
- [Engineering evidence](VALIDATION.md)

The video is an existing prototype recording; current cloud behavior is described in the architecture and validation documents. The live dashboard requires the configured caretaker account. Public visitors can inspect the sign-in screen and source; an authorized presenter demonstrates protected workflows. No public demo password is supplied.

## Suggested demonstration

| Time | Show | Explain |
|---|---|---|
| 0:00–0:25 | Problem and public application screen | Familiar faces, last-seen evidence and simple daily guidance. |
| 0:25–0:55 | Sign in; inspect recent preview and vision readiness | Camera JPEGs reach Northflank directly. Vercel serves the dashboard. |
| 0:55–1:30 | Ask about a supported object; open its memory photo | Show recorded time and available room label. A sighting can become stale. |
| 1:30–2:00 | Open an approved familiar-person profile or recognition result | Explain enrolled name, relationship, introduction and sample review. |
| 2:00–2:30 | Ask a question; use browser voice if supported and permission is granted | Gemini receives bounded text context; browser speech supplies audio. Typed input remains available. |
| 2:30–3:00 | Advance an approved routine; show Help status | Progress requires explicit confirmation. Notification delivery and human acknowledgement are separate. |

Sending an actual help notification should be intentional and coordinated with its recipient; viewing existing status is sufficient to explain this path.

## Before presenting

Check camera freshness, model readiness, image orientation, a suitable saved object event and approved person references. Use consented demonstration records. Check internet access and provider availability, and keep the existing video available if the live host is interrupted. A sign-in page or successful upload alone does not demonstrate completed inference.

The eight-photo capture workflow takes longer than this walkthrough. Demonstrate it separately: capture first, target eight suitable photos, then enter the name. The timeout can accept seven samples after 150 seconds. A fresh complete cloud enrollment remains a pending check in the report.

## Questions reviewers can trace into source

| Question | Source |
|---|---|
| How are camera uploads authenticated and queued? | [`app.py`](../sahayak_cloud/app.py), [API reference](API.md) |
| Where do object and face results come from? | [`vision.py`](../sahayak_cloud/vision.py), [`objects_onnx.py`](../sahayak_cloud/objects_onnx.py), [models](MODELS.md) |
| What makes personal memory persistent? | [`store.py`](../sahayak_cloud/store.py), [cloud guide](../deploy/CLOUD.md) |
| How are conversational actions constrained? | [`conversation.py`](../sahayak_cloud/conversation.py), [architecture](ARCHITECTURE.md) |
| What supports the test claims? | [Validation summary](VALIDATION.md), [`tests/`](../tests/) |

This prototype has not established clinical benefit, personal-object ownership, automatic positioning, medication ingestion, fall detection or an emergency-response service.
