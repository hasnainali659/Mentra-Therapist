from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum

from pydantic import BaseModel, Field


class TranscriptEntry(BaseModel):
    speaker: str
    text: str


class KeyMoment(BaseModel):
    type: str
    timestamp_offset_minutes: int
    content: str
    emotional_weight: float


class EmotionalTone(BaseModel):
    opening: str
    closing: str
    arc: str


class Session(BaseModel):
    session_id: str
    user_id: str
    session_number: int
    timestamp: datetime
    session_theme: str
    secondary_themes: list[str] = Field(default_factory=list)
    emotional_tone: EmotionalTone
    key_moments: list[KeyMoment] = Field(default_factory=list)
    unresolved_themes: list[str] = Field(default_factory=list)
    progress_markers: list[str] = Field(default_factory=list)
    user_commitments: list[str] = Field(default_factory=list)
    transcript: list[TranscriptEntry] = Field(default_factory=list)
    clinical_flags: list[str] = Field(default_factory=list)

    @property
    def closing_mood_score(self) -> int:
        return infer_mood_score(self.emotional_tone.closing)

    @property
    def session_date(self) -> str:
        return self.timestamp.date().isoformat()


class NotificationPreferences(BaseModel):
    opt_in: bool = True
    preferred_time: str | None = None
    preferred_channel: str | None = None


class PrivacySettings(BaseModel):
    allow_memory_storage: bool = True
    allow_semantic_search: bool = True
    user_can_delete_memories: bool = True
    data_retention_days: int | None = None


class UserProfile(BaseModel):
    user_id: str
    display_name: str
    created_at: datetime
    last_session_at: datetime
    days_since_last_session: int | None = None
    total_sessions: int
    persistent_themes: list[str] = Field(default_factory=list)
    overall_progress_direction: str | None = None
    known_strengths: list[str] = Field(default_factory=list)
    known_sensitivities: list[str] = Field(default_factory=list)
    active_commitments: list[str] = Field(default_factory=list)
    open_situations: list[str] = Field(default_factory=list)
    notification_preferences: NotificationPreferences = Field(
        default_factory=NotificationPreferences
    )
    privacy_settings: PrivacySettings = Field(default_factory=PrivacySettings)

    def computed_days_since_last_session(self) -> int:
        now = datetime.now(timezone.utc)
        last_session = self.last_session_at
        if last_session.tzinfo is None:
            last_session = last_session.replace(tzinfo=timezone.utc)
        return max((now - last_session).days, 0)


class MemoryType(str, Enum):
    theme = "theme"
    breakthrough = "breakthrough"
    commitment = "commitment"
    concern = "concern"


class ExtractedMemory(BaseModel):
    user_id: str
    session_id: str
    memory_text: str
    memory_type: MemoryType
    importance: float = Field(ge=0.0, le=1.0)
    session_date: str


class MemoryExtractionResponse(BaseModel):
    memories: list[ExtractedMemory]


class SessionOpenRequest(BaseModel):
    user_id: str
    current_context: str | None = None


class ReengagementRequest(BaseModel):
    user_id: str


def infer_mood_score(closing_tone: str) -> int:
    # hacky: maps a few words in the sample JSON to 1–10-ish for notification rules only
    text = closing_tone.lower()

    if any(keyword in text for keyword in ["distressed", "destabilised", "shaken"]):
        return 3
    if any(keyword in text for keyword in ["overwhelmed", "raw", "scared"]):
        return 4
    if any(keyword in text for keyword in ["relieved", "pensive", "cautious"]):
        return 5
    if any(keyword in text for keyword in ["steady", "hopeful", "grounded"]):
        return 7
    if any(keyword in text for keyword in ["energised", "good", "strong"]):
        return 8
    return 5
