# SAHAYAK API Reference

This reference documents the implemented Flask routes in [`sahayak_cloud/app.py`](../sahayak_cloud/app.py). Example names, IDs and credentials below are placeholders. The installation supports one patient profile, `patient_001`.

## Base URLs and conventions

- Local backend: `http://localhost:5000`
- Hosted frontend: use its same-origin `/api/...` paths, which Vercel rewrites to the Northflank HTTPS backend in cloud mode (or the configured tunnel in optional laptop mode).
- Camera ingestion uses `/upload`, not `/api/upload`. The camera sends directly to the HTTPS cloud backend, or the laptop LAN address in local mode.
- JSON requests use `Content-Type: application/json` unless an endpoint specifies multipart or binary data.
- Object endpoints generally return JSON. Image endpoints return `image/jpeg`.
- Database timestamps use ISO 8601 with timezone information. Daily routine times use local `HH:MM` values and the backend host's local date.
- Flask limits the overall request body to 6 MiB. The image decoder separately accepts up to 4 MiB of image bytes and rejects images above 16 million pixels. An upstream hosting proxy can impose additional limits.

IDs in route examples such as `{person_id}` are path placeholders. Replace them with the actual IDs returned by the API; do not include braces.

## Authentication

### Caretaker session

Most `/api` routes require a signed-in caretaker session. The cookie is HttpOnly and SameSite Strict, with a configured 12-hour session lifetime. Browser requests must preserve cookies. The frontend uses same-origin requests rather than cross-origin browser API calls.

Browser writes require an origin matching the backend host or an explicitly configured allowed origin. The API does not provide a general-purpose permissive CORS interface.

### Camera token

Device requests use `X-Device-Token`. Retrieve the installation's token through authenticated Settings. The token is not a caretaker session and does not grant access to protected photos or settings.

`POST /upload` permits token-free original firmware only while `allow_legacy_upload` is enabled. Its local default is `true` for legacy migration; new cloud installations default to `false` and the deployed installation rejects token-free uploads. Disable it after installing the updated firmware. `GET /api/device-config` always requires the token.

### Public routes

`GET /api/health`, the authentication route, frontend assets and the device endpoints have their own access rules. All other application routes listed below require a caretaker session unless explicitly stated otherwise.

## Errors and asynchronous results

Common error shape:

```json
{"error": "Explanation of the problem."}
```

| Status | Meaning |
| --- | --- |
| `200` | Request completed, including some updates or a paused camera upload |
| `201` | Person, sample, routine, answer or help request created |
| `202` | Camera frame or Telegram notification accepted into an in-memory queue |
| `400` | Invalid data, missing prerequisites or an unavailable operation |
| `401` | Missing/invalid caretaker session or required device token |
| `403` | Origin rejected, remote audio access, initial setup attempted remotely or restricted image path |
| `404` | Missing endpoint, record or evidence image, where the handler performs that check |
| `413` | Overall request body exceeds the Flask limit |
| `429` | Frame queue full or too many failed sign-in attempts |
| `500` | Unexpected server error with a sanitized JSON response |

`202` does not mean inference finished or Telegram delivery succeeded. Check status separately. Some mutation handlers return `{"ok": true}` without checking whether a row changed, so do not infer record existence solely from that response.

## Authentication and health

| Method | Path | Behavior |
| --- | --- | --- |
| `GET` | `/api/health` | Basic public process health; does not prove the models or camera are ready |
| `GET` | `/api/auth` | Return `configured`, `authenticated` and `local` booleans |
| `POST` | `/api/auth` | Create the initial local caretaker password or authenticate the existing caretaker |
| `DELETE` | `/api/auth` | Clear the current session |
| `GET` | `/api/status` | Authenticated device, model, worker, notification and audio status |

Authentication body:

```json
{"password": "YOUR_CARETAKER_PASSWORD"}
```

The initial password must contain at least ten characters and must be created from localhost. Later sign-in returns `{"ok": true}` and sets the session cookie. Eight attempts are allowed per visitor within a rolling 60-second window before `429`; successful authentication clears that visitor's attempt history.

Health response:

```json
{"service": "SAHAYAK", "status": "running"}
```

`/api/status` includes `devices`, `vision`, `queue`, `processed`, `last_error`, `last_processing_ms`, `last_queue_ms`, `listening`, `enrollment`, counts, recent `notifications`, `audio_error`, `local_audio` and `capture_enabled`. Device entries include freshness, online state, preview URL and a Wi-Fi setup URL when advertised by a camera on a private IPv4 address. Model readiness and labels appear under `vision`.

## Settings

`GET /api/settings` returns public settings and the device token to the authenticated caretaker. `PATCH /api/settings` validates and applies supplied writable settings, then returns the public settings object.

| Field | Default | Accepted values / behavior |
| --- | --- | --- |
| `patient_name` | `Your loved one` | Display name |
| `patient_introduction` | Empty string | Caretaker-written introduction |
| `room` | Empty string | Configured camera room; empty means unknown |
| `capture_interval` | `10` | Integer from 1 to 60 seconds |
| `capture_enabled` | `true` | Boolean |
| `camera_rotation` | `180` | `0` or `180` degrees |
| `language` | `en-IN` | Recognition language passed to the speech service |
| `face_threshold` | `0.50` | Number from `0.35` to `0.90` |
| `retention_days` | `30` | Integer from 1 to 3650 |
| `telegram_enabled` | `false` | Boolean |
| `telegram_chat` | Empty string | Intended recipient chat ID |
| `telegram_token` | Unset | Write-only through this API; blank updates retain the saved token |
| `ai_enabled` | `false` | Boolean; explicitly enables sharing limited text context with Gemini |
| `ai_model` | `gemini-3.8-flash` | `gemini-3.8-flash` or `gemini-3.5-flash-lite` |
| `gemini_api_key` | Unset | Write-only; blank retains the saved key, maximum 256 characters, no whitespace |
| `allow_legacy_upload` | `true` | Boolean; disable after updating camera firmware |

The response additionally includes `telegram_configured`, `ai_configured` and `device_token`. It does not return `telegram_token` or `gemini_api_key`. Unknown PATCH fields are ignored. Do not expose the settings response in a public repository or screenshot.

Example update:

```json
{"room": "Living room", "capture_interval": 2, "camera_rotation": 180, "allow_legacy_upload": false}
```

## Camera ingestion and configuration

### `POST /upload`

Preferred transport is a binary JPEG request with these headers:

```http
Content-Type: image/jpeg
X-Device-Token: YOUR_DEVICE_TOKEN
X-Device-Id: esp32-cam
X-Wifi-Setup: 1
```

`X-Device-Id` defaults to `esp32-cam` and must match `[A-Za-z0-9_-]{1,64}`. `X-Wifi-Setup: 1` advertises the camera's setup page; it is optional. The server derives the setup address from the observed private IPv4 client address, not a supplied forwarding header.

Legacy Base64 JSON is also accepted:

```json
{
  "patient_id": "patient_001",
  "device_id": "esp32-cam",
  "image": "BASE64_ENCODED_JPEG"
}
```

`P001` is accepted as a legacy patient alias. Other patient IDs are rejected.

Successful queue acceptance returns HTTP `202`:

```json
{"status": "queued", "capture_interval": 10}
```

When capture is paused, the endpoint returns HTTP `200` with `status: "paused"`. A full processing queue returns `429`. Successful upload is distinct from successful inference.

### `GET /api/device-config`

Requires `X-Device-Token` even when legacy uploads are enabled. Returns:

```json
{"capture_enabled": true, "capture_interval": 10}
```

During an active guided enrollment window, the reported interval becomes one second. The firmware normally polls configuration every four seconds.

### `GET /api/devices/{device_id}/image`

Requires a caretaker session. Returns the latest in-memory JPEG preview or an available disk fallback. Returns `404` when no image is available.

## People and face samples

| Method | Path | Input and result |
| --- | --- | --- |
| `GET` | `/api/people` | List active people, sample IDs/approval states, approved sample count and a photo URL |
| `POST` | `/api/people` | Create `name`, optional `relationship` and `introduction`; return `{"id": "..."}` with `201` |
| `PATCH` | `/api/people/{person_id}` | Update supplied `name`, `relationship` or `introduction`; return `{"ok": true}` |
| `DELETE` | `/api/people/{person_id}` | Soft-delete the profile; its samples no longer participate in matching |
| `POST` | `/api/people/{person_id}/samples` | Upload a reference photo or collect a fresh camera frame |
| `POST` | `/api/people/{person_id}/capture` | Start or stop guided capture |
| `PATCH` | `/api/samples/{sample_id}` | Set `approved` with a Boolean |
| `DELETE` | `/api/samples/{sample_id}` | Delete the sample row |
| `GET` | `/api/samples/{sample_id}/image` | Return the sample JPEG |

Create-person example:

```json
{"name": "Ananya", "relationship": "Daughter", "introduction": "She visits you on Sundays."}
```

To upload a sample, send multipart form data with an `image` file field. To capture from the camera, send JSON:

```json
{"device_id": "esp32-cam"}
```

The camera preview must be less than 30 seconds old. Samples require exactly one sufficiently large face. New samples return `201` with `{"id": "...", "approved": false}`. Creating a profile alone does not enable visual recognition; approved samples are required.

Guided capture accepts the same device JSON, targets six samples, and immediately attempts the latest fresh preview. The response includes `person_id`, `device_id`, `captured`, `target`, `started`, `last_sample`, `error` and `state`. States include `capturing`, `waiting_for_face`, `complete` and `timed_out`. Poll `/api/status` for progress. To stop, post `{"stop": true}` to the capture route.

Approval example:

```json
{"approved": true}
```

## Memory events and evidence

| Method | Path | Behavior |
| --- | --- | --- |
| `GET` | `/api/events` | List up to 500 active events, newest first |
| `GET` | `/api/events?q=phone` | Case-insensitive substring filter over stored object labels, person names and location |
| `GET` | `/api/events/{event_id}/image` | Return evidence JPEG |
| `GET` | `/api/events/{event_id}/image?annotated=1` | Return JPEG with stored object boxes and labels when available |
| `PATCH` | `/api/events/{event_id}` | Update `location`, `verified`, `objects` or `person_ids` |
| `DELETE` | `/api/events/{event_id}` | Hide the event through soft deletion |

Event objects contain `id`, `patient_id`, `device_id`, `first_seen`, `last_seen`, `location`, `location_source`, `people`, `objects`, `detections`, `verified`, `source`, `frames` and `image_url`. Raw image filesystem paths are omitted from event responses. `image_url` can be null.

Each detection contains a `label`, `score` and `box: [x1, y1, x2, y2]`. A `people` entry contains profile details and may contain a face similarity score.

Example correction:

```json
{"location": "Living room", "objects": ["cell phone", "chair"], "person_ids": ["PERSON_ID"], "verified": true}
```

Object and person corrections mark the event verified. A location update records `location_source: "caretaker"`. Image evidence may be unavailable after retention or cleanup; callers must handle `404`.

## Questions and memory retrieval

`POST /api/query` accepts:

```json
{"text": "Where is my daughter?"}
```

Optional `person` and `object` fields provide explicit filters. `person` is a person name, not a profile ID. `/query` is a session-protected legacy alias for the same handler.

With AI enabled and configured, natural conversation uses Gemini and a limited text snapshot of saved records. The optional `history` array carries at most 12 messages, each `{ "role": "user" | "assistant", "content": "..." }`, with at most 2,000 characters per content. The current `text` also accepts at most 2,000 characters. History contains previous turns only. Explicit `person`/`object` filters apply to local retrieval; phrase the filter in `text` for AI conversation.

Successful cloud replies include `engine: "gemini"`, `model` and `latency_ms`. Local replies include `engine: "local"`; an attempted cloud request that fails also includes a sanitized `ai_notice`. These failures normally still return HTTP 200 with a local answer. No API key is included in query output. General conversation uses status `conversation`; existing evidence, routine and help response fields remain available.

### `POST /api/ai/test`

Authenticated connection test using the saved Gemini key and model. Sends a generic greeting request with empty personal context. Returns `{ "ok": true, "response": "...", "latency_ms": 1234 }`. A missing key returns 400. Provider access/quota/network/output failures return 503 with a sanitized `error`. Save new preferences before testing.

The examples below describe local fallback behavior; with Gemini enabled, varied wording and follow-up questions are also accepted.

| Example text | Implemented behavior |
| --- | --- |
| `Who is my daughter?` | Resolve the enrolled relationship and return name/introduction |
| `Who is Ananya?` | Return that enrolled person's relationship/introduction |
| `Where is my daughter?` | Resolve one enrolled person and search past sightings; clarify if ambiguous |
| `Have you seen my phone?` | Search the last recorded `cell phone` observation and explain ownership uncertainty |
| `Who is this?` | Introduce a recently identified person when a camera sighting is less than 30 seconds old |
| `What is my schedule?` | List enabled routines in time order with completed/next-step status |
| `What should I do next?` | Select the next unfinished routine step using the current local time |
| `Sahayak help` | Save help, attempt to queue a Telegram alert and include today's schedule |
| A saved approved question | Return the active caretaker-approved exact answer when that branch matches |

Responses always include `status` and `response`, and may include `event`, `people`, `routine`, `routines` or `help`.

Query statuses are `conversation`, `found`, `approved`, `routine`, `schedule`, `help`, `clarify`, `not_found` and `unconfirmed`. Local lookups without matching observations return `not_found`. Local medication-related questions take a safety response before ordinary retrieval. Cloud replies are instructed to use supplied personal facts and avoid unsupported medication advice; model correctness is not guaranteed.

## Capture a person before naming

`POST /api/enrollment/start` accepts `{}` (most recently seen device) or `{ "device_id": "esp32-cam" }`. Requires a ready face model, enabled uploads and a frame from the last 30 seconds. Returns 201 with `id`, `device_id`, `state`, `captured`, `target: 8`, `guidance`, and optional `person_id`. Exact commands such as `Record a person` through `/api/query` or `/api/audio/listen` start the same flow without an LLM; Gemini can route varied enrollment requests to this action too.

`GET /api/status` includes `recording` with the same public state. Capture checks one sufficiently large face, exposure, sharpness, perceptual difference and similarity to the first face. It saves eight distinct samples, at least one second apart, or accepts seven after the 150-second deadline. State progresses from `capturing` to `awaiting_name`, `timed_out` or `saved`. These checks reduce poor samples and mixed identities; they cannot guarantee recognition accuracy.

`GET /api/enrollment/{id}/photos/{index}` serves an authenticated selected image (zero-based index). Pending paths/embeddings are not returned in JSON or shared with Gemini. Images stay on the laptop.

`POST /api/enrollment/{id}/finish` accepts `{ "name": "Ayush", "relationship": "Brother" }` (relationship optional). Requires `awaiting_name` and at least seven photos. Creates one profile and approved samples atomically; returns 201 with `id`, `name`, and `samples`. Repeated completion returns the existing profile. Explicitly submitting the name approves this recording for recognition; manual enrollment remains individually reviewed.

`DELETE /api/enrollment/{id}` cancels and deletes unsaved temporary photos. Saved profiles/photos remain. Only one quick capture can run, and it excludes simultaneous manual guided capture. A restart drops unfinished capture state; orphan photos are removed by normal maintenance after one hour.

`POST /api/audio/listen` with `{ "purpose": "person_name" }` transcribes a name only and returns `{ "text": "..." }`; it does not query Gemini or trigger assistance. The naming UI then submits the name to the finish endpoint. Microphone control remains localhost-only and requires clicking its microphone button.

## Routine and approved-answer endpoints

| Method | Path | Behavior |
| --- | --- | --- |
| `GET` | `/api/routines` | List non-deleted routines, including disabled ones, with today's step progress |
| `POST` | `/api/routines` | Create `title`, `time` and nonempty `steps`; return ID with `201` |
| `PATCH` | `/api/routines/{routine_id}` | Edit `title`, `time`, `steps` or `enabled`; advance/reset with `action` |
| `DELETE` | `/api/routines/{routine_id}` | Soft-delete the routine |
| `GET` | `/api/answers` | List non-deleted approved question/answer records, including stored expiry |
| `POST` | `/api/answers` | Create `question`, `answer` and optional ISO `expires`; return ID with `201` |
| `DELETE` | `/api/answers/{answer_id}` | Soft-delete an approved answer |
| `GET` | `/api/recap` | Return today's verified events and routines whose steps are complete |

Create-routine example:

```json
{"title": "Morning routine", "time": "09:00", "steps": ["Sit at the table", "Have breakfast"]}
```

Times must match 24-hour `HH:MM`. Step lists must contain nonempty strings. To advance one step, PATCH `{"action": "done"}`. To reset today's progress, PATCH `{"action": "reset"}`. Progress cannot advance beyond the last step. Changing the step list clears today's saved progress.

Approved-answer example:

```json
{"question": "When is our walk?", "answer": "We plan to walk after breakfast.", "expires": "2026-10-18T12:00:00+05:30"}
```

Expired answers stay in the list but are ignored during answer retrieval. Matching normalizes case and surrounding spaces/question marks; it is not semantic matching.

## Telegram and help requests

| Method | Path | Behavior |
| --- | --- | --- |
| `POST` | `/api/telegram` | Queue a connection test or a selected memory photo |
| `GET` | `/api/help` | List up to 50 latest requests with joined notification delivery status/error |
| `POST` | `/api/help` | Save a help request and attempt Telegram notification; return `201` |
| `PATCH` | `/api/help/{help_id}` | Mark a request acknowledged and set its acknowledgement timestamp |

Send a connection test with `{}` or send an evidence photo with `{"event_id": "EVENT_ID"}`. Telegram must be configured and enabled. A selected event must have an available image. The Telegram route returns HTTP `202` with `{"id": "...", "status": "queued"}`.

Create-help example:

```json
{"message": "Please come and help me."}
```

The response contains `id`, `status: "requested"`, `delivery` and `notification`. Delivery initially reports `queued`, `not configured; saved on this laptop`, or `failed; saved on this laptop`. The request remains recorded even if Telegram cannot be queued.

Notification states are `queued`, `sent` and `failed`. The worker attempts delivery up to three times. `sent` means Telegram accepted the request, not that the recipient read it. Help acknowledgement is a separate dashboard action. Recent notification results appear in `/api/status`; help listing joins delivery status to the request.

## Laptop audio

All audio routes require both a caretaker session and a local request. Tunneled visitors receive `403` even if their connection reaches Flask over loopback.

| Method | Path | Request | Result |
| --- | --- | --- | --- |
| `POST` | `/api/audio/listen` | `{}` | Record the laptop microphone, transcribe and run the query handler |
| `POST` | `/api/audio/speak` | `{"text": "Your answer here."}` | Queue a laptop spoken reply, returning `status: "queued"` |
| `POST` | `/api/audio/cancel` | `{}` | Request microphone cancellation, returning `status: "cancelling"` |

The listen response includes `text` for the transcript plus `response` and the query result fields. Display `response` as the assistant answer rather than displaying the transcript again. Listening does not automatically enqueue speech; the frontend separately calls `/api/audio/speak`.

Speech recognition uses an external service and may require internet. Speaker acceptance is not proof of audible playback. Audio errors appear in `/api/status`. Cancellation applies to microphone listening rather than flushing all queued speaker replies.

## Camera setup web interface

These routes run on the ESP32 itself, not Flask:

| Method | Camera path | Access |
| --- | --- | --- |
| `GET` | `/` | Basic authentication with username `caretaker` and the camera's unique setup password |
| `POST` | `/save` | Same authentication plus the setup form's `nonce` |

The save form uses `ssid`, `password`, `address`, `nonce` and optional `open=yes` for a password-free Wi-Fi network. Leave the password blank only to retain the saved password for the same SSID. The laptop address must use local HTTP with a private IPv4 host and a valid port.

The setup page is normally reachable at the camera's LAN address or through supported mDNS at `http://sahayak-camera.local/`. During recovery, connect to the camera's protected access point and use `http://192.168.4.1/`. The setup password is separate from the dashboard password and appears on USB serial at 115200 baud.

Related documentation: [Architecture](ARCHITECTURE.md), [Models](MODELS.md), [Installation](SETUP.md).
