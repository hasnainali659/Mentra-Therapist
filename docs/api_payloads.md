# API request payloads

Base URL in examples: `http://127.0.0.1:8000` (change if you run uvicorn elsewhere).

Sample user id from `sessions/user_profile.json`: **`user_aisha_001`**.

---

## 1. `POST /ingest-all`

**Body:** none (empty body is fine).

```bash
curl -s -X POST http://127.0.0.1:8000/ingest-all
```

Optional explicit empty JSON (also accepted by FastAPI):

```json
{}
```

```bash
curl -s -X POST http://127.0.0.1:8000/ingest-all -H "Content-Type: application/json" -d "{}"
```

---

## 2. `POST /session-open`

**JSON schema:** `user_id` (required), `current_context` (optional string).

### Minimal (no extra context)

```json
{
  "user_id": "user_aisha_001"
}
```

### With context (steers memory search + opener)

```json
{
  "user_id": "user_aisha_001",
  "current_context": "check in on work stress and how the week felt"
}
```

**curl (Git Bash / macOS / Linux)**

```bash
curl -s -X POST http://127.0.0.1:8000/session-open \
  -H "Content-Type: application/json" \
  -d "{\"user_id\":\"user_aisha_001\",\"current_context\":\"check in on work stress\"}"
```

---

## 3. `POST /reengagement-check`

**JSON schema:** `user_id` (required).

```json
{
  "user_id": "user_aisha_001"
}
```

**curl**

```bash
curl -s -X POST http://127.0.0.1:8000/reengagement-check \
  -H "Content-Type: application/json" \
  -d "{\"user_id\":\"user_aisha_001\"}"
```