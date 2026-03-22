from __future__ import annotations

import json
from typing import Any
from uuid import uuid5, NAMESPACE_URL
from pathlib import Path

import httpx
from langchain_core.documents import Document
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from openai import APIConnectionError, APIError, APITimeoutError, RateLimitError
from pydantic import ValidationError
from langchain_qdrant import QdrantVectorStore
from qdrant_client import QdrantClient
from qdrant_client.http.models import Distance, FieldCondition, Filter, MatchValue, VectorParams

from src.config import Settings
from src.models import ExtractedMemory, MemoryExtractionResponse, Session, UserProfile

# Errors where retrying with OpenAI chat is reasonable (network, provider 5xx, rate limits, etc.)
_CHAT_FALLBACK_EXCEPTIONS: tuple[type[BaseException], ...] = (
    APIConnectionError,
    APITimeoutError,
    RateLimitError,
    APIError,
    httpx.ConnectError,
    httpx.ReadTimeout,
    httpx.WriteTimeout,
    httpx.RemoteProtocolError,
    json.JSONDecodeError,
    ValidationError,
)


EXTRACTION_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            (
                "Pull 3–6 short memories from this therapy-style session. "
                "They should be useful later for continuity or a gentle check-in. "
                "No diagnoses, no long quotes, skip irrelevant personal detail. "
                "Types: theme, breakthrough, commitment, concern."
            ),
        ),
        (
            "human",
            (
                "Extract memories from this session.\n\n"
                "User profile summary:\n{profile_summary}\n\n"
                "Session JSON:\n{session_json}"
            ),
        ),
    ]
)


OPENING_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            (
                "Write 2–4 sentences opening a follow-up session. Warm, plain language. "
                "Don’t say you looked anything up or mention databases. "
                "Hint at what mattered last time without quoting chunks of transcript."
            ),
        ),
        (
            "human",
            (
                "User name: {display_name}\n"
                "Current context: {current_context}\n"
                "Relevant past memories:\n{memory_bullets}\n"
                "Open situations:\n{open_situations}"
            ),
        ),
    ]
)


def load_user_profile(settings: Settings) -> UserProfile:
    profile_path = settings.sessions_dir / "user_profile.json"
    return UserProfile.model_validate_json(profile_path.read_text(encoding="utf-8"))


def load_sessions(settings: Settings) -> list[Session]:
    session_paths = sorted(Path(settings.sessions_dir).glob("session_*.json"))
    sessions = [
        Session.model_validate_json(path.read_text(encoding="utf-8")) for path in session_paths
    ]
    return sorted(sessions, key=lambda session: session.timestamp)


def get_embeddings(settings: Settings) -> OpenAIEmbeddings:
    return OpenAIEmbeddings(
        model=settings.openai_embedding_model,
        api_key=settings.openai_api_key,
    )


def get_chat_model(settings: Settings, temperature: float = 0.1) -> Any:
    """Primary: DeepSeek (OpenAI-compatible). On provider/network errors, OpenAI chat."""
    deepseek = ChatOpenAI(
        model=settings.deepseek_model,
        api_key=settings.deepseek_api_key,
        base_url=settings.deepseek_base_url,
        temperature=temperature,
    )
    openai_chat = ChatOpenAI(
        model=settings.openai_model,
        api_key=settings.openai_api_key,
        temperature=temperature,
    )
    return deepseek.with_fallbacks(
        [openai_chat],
        exceptions_to_handle=_CHAT_FALLBACK_EXCEPTIONS,
    )


def get_qdrant_client(settings: Settings) -> QdrantClient:
    return QdrantClient(url=settings.qdrant_url, check_compatibility=False)


def ensure_collection(settings: Settings) -> None:
    client = get_qdrant_client(settings)
    collections = client.get_collections().collections
    collection_names = {collection.name for collection in collections}
    if settings.qdrant_collection_name not in collection_names:
        client.create_collection(
            collection_name=settings.qdrant_collection_name,
            vectors_config=VectorParams(size=1536, distance=Distance.COSINE),
        )


def get_vector_store(settings: Settings) -> QdrantVectorStore:
    ensure_collection(settings)
    return QdrantVectorStore(
        client=get_qdrant_client(settings),
        collection_name=settings.qdrant_collection_name,
        embedding=get_embeddings(settings),
    )


def count_stored_memories(settings: Settings) -> int:
    ensure_collection(settings)
    client = get_qdrant_client(settings)
    count_result = client.count(collection_name=settings.qdrant_collection_name, exact=True)
    return int(count_result.count)


def build_profile_summary(profile: UserProfile) -> str:
    parts = [
        f"Name: {profile.display_name}",
        f"Persistent themes: {', '.join(profile.persistent_themes)}",
        f"Known sensitivities: {', '.join(profile.known_sensitivities)}",
        f"Active commitments: {', '.join(profile.active_commitments)}",
    ]
    return "\n".join(parts)


def extract_memories_from_session(
    settings: Settings, profile: UserProfile, session: Session
) -> list[ExtractedMemory]:
    chain = EXTRACTION_PROMPT | get_chat_model(settings).with_structured_output(
        MemoryExtractionResponse
    )
    result = chain.invoke(
        {
            "profile_summary": build_profile_summary(profile),
            "session_json": json.dumps(session.model_dump(mode="json"), indent=2),
        }
    )

    cleaned_memories: list[ExtractedMemory] = []
    for memory in result.memories:
        cleaned_memories.append(
            memory.model_copy(
                update={
                    "user_id": session.user_id,
                    "session_id": session.session_id,
                    "session_date": session.session_date,
                }
            )
        )
    return cleaned_memories


def store_memories(
    settings: Settings, memories: list[ExtractedMemory]
) -> dict[str, int | str]:
    vector_store = get_vector_store(settings)
    documents: list[Document] = []
    ids: list[str] = []

    for index, memory in enumerate(memories):
        memory_id = str(uuid5(NAMESPACE_URL, f"{memory.session_id}_{index}"))
        ids.append(memory_id)
        documents.append(
            Document(
                page_content=memory.memory_text,
                metadata={
                    "memory_id": memory_id,
                    "user_id": memory.user_id,
                    "session_id": memory.session_id,
                    "memory_type": memory.memory_type.value,
                    "importance": memory.importance,
                    "session_date": memory.session_date,
                },
            )
        )

    vector_store.add_documents(documents=documents, ids=ids)
    return {"stored_memories": len(documents)}


def ingest_all_sessions(settings: Settings) -> dict[str, int | str]:
    profile = load_user_profile(settings)
    sessions = load_sessions(settings)

    total_memories = 0
    for session in sessions:
        memories = extract_memories_from_session(settings, profile, session)
        store_memories(settings, memories)
        total_memories += len(memories)

    return {
        "user_id": profile.user_id,
        "sessions_ingested": len(sessions),
        "memories_stored": total_memories,
    }


def retrieve_relevant_memories(
    settings: Settings, user_id: str, query: str, limit: int = 4
) -> list[ExtractedMemory]:
    vector_store = get_vector_store(settings)
    meta_key = vector_store.metadata_payload_key
    qdrant_filter = Filter(
        must=[
            FieldCondition(
                key=f"{meta_key}.user_id",
                match=MatchValue(value=user_id),
            )
        ]
    )
    documents = vector_store.similarity_search(query=query, k=limit, filter=qdrant_filter)

    memories: list[ExtractedMemory] = []
    for document in documents:
        metadata = document.metadata
        memories.append(
            ExtractedMemory(
                user_id=metadata["user_id"],
                session_id=metadata["session_id"],
                memory_text=document.page_content,
                memory_type=metadata["memory_type"],
                importance=float(metadata["importance"]),
                session_date=metadata["session_date"],
            )
        )
    return memories


def generate_session_opening(
    settings: Settings, user_id: str, current_context: str | None = None
) -> dict[str, object]:
    profile = load_user_profile(settings)
    if profile.user_id != user_id:
        raise ValueError(f"Unknown user_id: {user_id}")

    query = current_context or "What should a therapist gently remember at the start of the next session?"
    memories = retrieve_relevant_memories(settings, user_id, query=query, limit=4)

    memory_bullets = "\n".join(
        f"- {memory.memory_text} ({memory.memory_type.value})" for memory in memories
    )
    open_situations = "\n".join(f"- {item}" for item in profile.open_situations)

    chain = OPENING_PROMPT | get_chat_model(settings, temperature=0.4)
    message = chain.invoke(
        {
            "display_name": profile.display_name,
            "current_context": current_context or "General follow-up session",
            "memory_bullets": memory_bullets or "- No prior memories available.",
            "open_situations": open_situations or "- None.",
        }
    )

    return {
        "user_id": user_id,
        "opening_message": message.content,
        "memories_used": [memory.model_dump() for memory in memories],
    }
