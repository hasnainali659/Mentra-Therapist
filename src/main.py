from fastapi import FastAPI, HTTPException

from src.config import get_settings
from src.memory_pipeline import (
    generate_session_opening,
    get_qdrant_client,
    ingest_all_sessions,
)
from src.models import ReengagementRequest, SessionOpenRequest
from src.reengagement import build_reengagement_check, example_notification_scenarios


app = FastAPI(title="recall-api", version="0.1.0")


@app.get("/health")
def health() -> dict[str, str]:
    settings = get_settings()
    client = get_qdrant_client(settings)
    client.get_collections()
    return {"status": "ok"}


@app.post("/ingest-all")
def ingest_all() -> dict[str, int | str]:
    settings = get_settings()
    return ingest_all_sessions(settings)


@app.post("/session-open")
def session_open(request: SessionOpenRequest) -> dict[str, object]:
    settings = get_settings()
    try:
        return generate_session_opening(
            settings=settings,
            user_id=request.user_id,
            current_context=request.current_context,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.post("/reengagement-check")
def reengagement_check(request: ReengagementRequest) -> dict[str, object]:
    settings = get_settings()
    try:
        result = build_reengagement_check(settings, request.user_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    result["example_scenarios"] = example_notification_scenarios()
    return result
