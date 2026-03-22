from __future__ import annotations

import gradio as gr
from langchain_core.prompts import ChatPromptTemplate

from src.config import get_settings
from src.memory_pipeline import (
    count_stored_memories,
    generate_session_opening,
    get_chat_model,
    ingest_all_sessions,
    load_sessions,
    load_user_profile,
    retrieve_relevant_memories,
)


CHAT_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            (
                "You’re playing a supportive therapist in a prototype — not giving medical advice. "
                "Keep replies short and conversational. Don’t sound like a form letter. "
                "It’s fine to say you’re not sure. Use the background info if it helps, don’t force it."
            ),
        ),
        (
            "human",
            (
                "User profile:\n{profile_summary}\n\n"
                "Recent session summaries:\n{session_summaries}\n\n"
                "Relevant memories:\n{memory_summaries}\n\n"
                "Conversation so far:\n{chat_history}\n\n"
                "Latest user message:\n{user_message}"
            ),
        ),
    ]
)


def format_profile_markdown() -> str:
    settings = get_settings()
    profile = load_user_profile(settings)

    themes = "\n".join(f"- {item}" for item in profile.persistent_themes)
    strengths = "\n".join(f"- {item}" for item in profile.known_strengths)
    commitments = "\n".join(f"- {item}" for item in profile.active_commitments)
    situations = "\n".join(f"- {item}" for item in profile.open_situations)

    return (
        f"## Profile\n"
        f"**Name:** {profile.display_name}\n\n"
        f"**Total sessions:** {profile.total_sessions}\n\n"
        f"**Overall progress:** {profile.overall_progress_direction}\n\n"
        f"**Persistent themes:**\n{themes}\n\n"
        f"**Known strengths:**\n{strengths}\n\n"
        f"**Active commitments:**\n{commitments}\n\n"
        f"**Open situations:**\n{situations}"
    )


def format_sessions_markdown() -> str:
    settings = get_settings()
    sessions = load_sessions(settings)

    blocks: list[str] = ["## Past sessions"]
    for session in sessions:
        key_points = [moment.content for moment in session.key_moments[:2]]
        points_text = "\n".join(f"- {point}" for point in key_points)
        blocks.append(
            (
                f"**Session {session.session_number}: {session.session_theme}**\n"
                f"- Date: {session.session_date}\n"
                f"- Closing tone: {session.emotional_tone.closing}\n"
                f"- Unresolved themes: {', '.join(session.unresolved_themes) or 'None'}\n"
                f"{points_text}"
            )
        )
    return "\n\n".join(blocks)


def build_profile_summary_text() -> str:
    settings = get_settings()
    profile = load_user_profile(settings)
    return (
        f"Name: {profile.display_name}\n"
        f"Persistent themes: {', '.join(profile.persistent_themes)}\n"
        f"Known sensitivities: {', '.join(profile.known_sensitivities)}\n"
        f"Active commitments: {', '.join(profile.active_commitments)}\n"
        f"Open situations: {', '.join(profile.open_situations)}"
    )


def build_session_summaries_text() -> str:
    settings = get_settings()
    sessions = load_sessions(settings)
    summary_lines = []
    for session in sessions:
        summary_lines.append(
            f"Session {session.session_number}: {session.session_theme}. "
            f"Closing tone: {session.emotional_tone.closing}. "
            f"Main unresolved themes: {', '.join(session.unresolved_themes[:2]) or 'None'}."
        )
    return "\n".join(summary_lines)


def ensure_demo_memories() -> str:
    settings = get_settings()
    stored_memories = count_stored_memories(settings)
    if stored_memories > 0:
        return f"Demo memory store already ready with {stored_memories} memories."

    result = ingest_all_sessions(settings)
    return (
        f"Demo memory store ready. "
        f"Ingested {result['sessions_ingested']} sessions and stored {result['memories_stored']} memories."
    )


def start_chat() -> tuple[list[dict[str, str]], str]:
    settings = get_settings()
    profile = load_user_profile(settings)
    ensure_demo_memories()
    opener = generate_session_opening(settings, profile.user_id)
    history = [{"role": "assistant", "content": opener["opening_message"]}]
    memories_used = opener["memories_used"]
    memory_text = "\n".join(
        f"- {item['memory_text']} ({item['memory_type']})" for item in memories_used
    ) or "- No memories used."
    return history, f"## Retrieved memories\n{memory_text}"


def chat(
    message: str, history: list[dict[str, str]] | None
) -> tuple[list[dict[str, str]], str, str]:
    settings = get_settings()
    profile = load_user_profile(settings)
    history = history or []

    retrieved_memories = retrieve_relevant_memories(
        settings=settings,
        user_id=profile.user_id,
        query=message,
        limit=4,
    )

    memory_summaries = "\n".join(
        f"- {memory.memory_text} ({memory.memory_type.value})"
        for memory in retrieved_memories
    ) or "- No relevant memories found."

    chat_history_text = "\n".join(
        f"{entry['role']}: {entry['content']}" for entry in history[-8:]
    )

    chain = CHAT_PROMPT | get_chat_model(settings, temperature=0.5)
    response = chain.invoke(
        {
            "profile_summary": build_profile_summary_text(),
            "session_summaries": build_session_summaries_text(),
            "memory_summaries": memory_summaries,
            "chat_history": chat_history_text or "No previous chat history.",
            "user_message": message,
        }
    )

    history = history + [
        {"role": "user", "content": message},
        {"role": "assistant", "content": response.content},
    ]

    return history, "", f"## Retrieved memories\n{memory_summaries}"


def build_app() -> gr.Blocks:
    with gr.Blocks(title="recall-chat") as demo:
        gr.Markdown("# Recall prototype")
        gr.Markdown(
            "Left side: static stuff from the JSON files. Right side: chat uses Qdrant retrieval + the same model as the API. "
            "Hit “prepare” once if the vector DB is empty."
        )

        with gr.Row():
            with gr.Column(scale=1):
                profile_box = gr.Markdown(value=format_profile_markdown())
                sessions_box = gr.Markdown(value=format_sessions_markdown())
                memory_box = gr.Markdown(value="## Retrieved memories\n(nothing yet — start chat or hit prepare)")
                prepare_button = gr.Button("Prepare Demo Memories")
                prepare_status = gr.Textbox(label="Status", interactive=False)
            with gr.Column(scale=2):
                chatbot = gr.Chatbot(label="Chat")
                start_button = gr.Button("Start With Warm Opener")
                msg = gr.Textbox(label="Your message", placeholder="Type a message...")
                send_button = gr.Button("Send")

        prepare_button.click(fn=ensure_demo_memories, outputs=prepare_status)
        start_button.click(fn=start_chat, outputs=[chatbot, memory_box])
        send_button.click(fn=chat, inputs=[msg, chatbot], outputs=[chatbot, msg, memory_box])
        msg.submit(fn=chat, inputs=[msg, chatbot], outputs=[chatbot, msg, memory_box])

    return demo


if __name__ == "__main__":
    build_app().launch()
