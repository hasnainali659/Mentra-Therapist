# Project Recall (take-home)

Small demo for Mentra’s assessment: pull a few sessions from JSON, turn them into short “memories”, stick them in Qdrant, then use retrieval + an LLM to open a new session in a human way. There’s also a dumb rule-based re-engagement stub and a Gradio page if you want to click around instead of curl.

Chat completions use **DeepSeek** first (OpenAI-compatible API); if the call fails (network, rate limits, bad JSON from structured output, etc.), the same prompt is retried with **OpenAI** (`OPENAI_MODEL`, default `gpt-4o-mini`). **Embeddings stay on OpenAI** (`text-embedding-3-small`).

## What’s in the repo

| Path | What it does |
|------|----------------|
| `src/main.py` | FastAPI: health, ingest, session opener, re-engagement |
| `src/config.py` | Loads `.env` (keys, Qdrant URL, model names) |
| `src/models.py` | Pydantic models for sessions/profile/API bodies |
| `src/memory_pipeline.py` | Extract memories, embed, Qdrant, opener generation |
| `src/reengagement.py` | Rules + example push copy |
| `gradio_app.py` | Optional UI |
| `sessions/` | Sample data |
| `docs/memory_architecture.md` | Design write-up for the brief |
| `docs/ethical_risk_analysis.md` | Short ethics note |
| `docs/api_payloads.md` | Example JSON bodies + curl for each endpoint |
| `docs/gradio_test_questions.md` | Questions to exercise Gradio chat + retrieval |
| `architecture.md` | Longer walkthrough if someone wants diagrams |

## Setup

Python 3.10+, Docker if you’re running Qdrant locally, an **OpenAI** key (embeddings), and a **DeepSeek** key (chat / memory extraction / opener).

```bash
python -m venv .venv
.venv\Scripts\activate   # Windows
pip install -r requirements.txt
```

Copy `.env.example` → `.env` and set `OPENAI_API_KEY` and `DEEPSEEK_API_KEY`. If Qdrant isn’t already running on 6333:

```bash
docker compose up -d
```

API:

```bash
uvicorn src.main:app --reload
```

Gradio (optional):

```bash
python gradio_app.py
```

## API quick reference

- `GET /health` — app + can reach Qdrant  
- `POST /ingest-all` — processes everything under `sessions/session_*.json`  
- `POST /session-open` — body: `{"user_id":"...","current_context":"optional"}`  
- `POST /reengagement-check` — body: `{"user_id":"..."}`  

Examples (from another terminal while `uvicorn` is running):

```bash
curl -s -X POST http://127.0.0.1:8000/ingest-all
curl -s -X POST http://127.0.0.1:8000/session-open -H "Content-Type: application/json" -d "{\"user_id\":\"user_aisha_001\",\"current_context\":\"check in on work stress\"}"
```

On Windows PowerShell you may need to escape quotes differently — Postman works fine too. **Copy-paste payloads:** see [`docs/api_payloads.md`](docs/api_payloads.md).

## Future 2 Weeks Plan

Deep agent workflows for long term and persistent memory