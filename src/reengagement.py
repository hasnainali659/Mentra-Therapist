from __future__ import annotations

from src.config import Settings
from src.memory_pipeline import load_sessions, load_user_profile


def build_reengagement_check(settings: Settings, user_id: str) -> dict[str, object]:
    profile = load_user_profile(settings)
    if profile.user_id != user_id:
        raise ValueError(f"Unknown user_id: {user_id}")

    sessions = load_sessions(settings)
    last_session = sessions[-1]
    days_since = profile.computed_days_since_last_session()
    mood_score = last_session.closing_mood_score
    unresolved_themes = last_session.unresolved_themes
    clinical_flags = last_session.clinical_flags

    should_send = days_since >= 5 and profile.notification_preferences.opt_in

    if mood_score <= 4:
        scenario = "supportive_follow_up"
        copy = (
            "Hi Aisha, I know things felt heavy last time. No pressure at all, "
            "but if it would help to have a space to sort through what is still sitting with you, "
            "I'm here when you're ready."
        )
    elif unresolved_themes and days_since >= 7:
        scenario = "gentle_reconnect"
        copy = (
            "Hi Aisha, I've been thinking about the questions you were starting to explore around "
            "what you want from your career. If you want to pick that thread back up, we can take it one step at a time."
        )
    else:
        scenario = "momentum_nudge"
        copy = (
            "Hi Aisha, you made some meaningful shifts recently. If you want, we can keep building on that momentum "
            "and check in on how the week has felt for you."
        )

    return {
        "user_id": user_id,
        "should_send": should_send,
        "days_since_last_session": days_since,
        "closing_mood_score": mood_score,
        "unresolved_themes": unresolved_themes,
        "clinical_flags": clinical_flags,
        "scenario": scenario,
        "notification_copy": copy,
    }


def example_notification_scenarios() -> list[dict[str, object]]:
    return [
        {
            "scenario": "gentle_momentum",
            "signals": {
                "days_since_last_session": 5,
                "closing_mood_score": 7,
                "active_commitment": "career reflection writing exercise",
            },
            "notification_copy": (
                "Hi Aisha, last time you were starting to get clearer on what you want from your career. "
                "If you want to keep exploring that, we can pick it up from there."
            ),
        },
        {
            "scenario": "distress_follow_up",
            "signals": {
                "days_since_last_session": 4,
                "closing_mood_score": 4,
                "clinical_flag": "sleep disruption and isolation",
            },
            "notification_copy": (
                "Hi Aisha, just a gentle check-in. You do not have to carry everything alone, "
                "and this space is here whenever it feels right to come back."
            ),
        },
        {
            "scenario": "breakthrough_build",
            "signals": {
                "days_since_last_session": 8,
                "closing_mood_score": 6,
                "unresolved_theme": "career direction",
            },
            "notification_copy": (
                "Hi Aisha, something important seemed to shift in the way you were thinking about your future. "
                "Whenever you're ready, we can keep exploring that with care."
            ),
        },
    ]
