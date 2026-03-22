# Gradio — questions to test the app end-to-end

Use these **after** you’ve run the API stack (Qdrant + keys in `.env`) and started `python gradio_app.py`.

## Suggested order (covers all UI paths)

1. **Prepare Demo Memories** — Confirms ingest → Qdrant (or “already ready”).
2. **Start With Warm Opener** — Confirms `/session-open`-style flow: retrieval + LLM opener + “Retrieved memories” panel.
3. **Send** the questions below in order (or pick by section).

---

## A. Retrieval & “remember me” (core product)

These should pull **different** memory snippets in the right-hand **Retrieved memories** panel. Watch for overlap with session themes in the sidebar.

| # | Paste this in chat | What you’re checking |
|---|--------------------|----------------------|
| 1 | I’m still drowning in work stress and my manager — can we pick up from last time? | Workplace + manager themes; memories should mention stress/authority if ingest worked. |
| 2 | I’ve been trying to set boundaries at work but it’s scary. Any thoughts? | Session 3 “boundaries / identity”; retrieval should surface boundary-related memories. |
| 3 | After that confrontation with my manager I’ve been second-guessing everything. | Session 4 “confrontation aftermath”; should retrieve conflict / self-doubt style memories. |
| 4 | I want to talk about resilience and sitting with uncertainty instead of fixing everything. | Session 5 theme; tests semantic match on “resilience / uncertainty”. |
| 5 | Impostor syndrome is loud again — especially after performance reviews. | Profile + sessions on performance / self-worth; tests theme + keyword overlap. |
| 6 | What were the small commitments I said I’d try between sessions? | Tests whether **commitment**-type memories appear (if the extractor labeled any). |

---

## B. Multi-turn conversation

Start from a **Start With Warm Opener** or send **#1** first, then:

| # | Follow-up | What you’re checking |
|---|------------|----------------------|
| 7 | That resonates. What’s one tiny step I could try this week? | Reply stays short/supportive; may still show retrieved memories relevant to prior turn. |
| 8 | Actually the harder part is guilt when I rest. | New query vector; panel should update — not stay stuck on only “work stress”. |
| 9 | Can you summarize what we’ve covered so far in this chat? | Coherence with `chat_history` in the prompt (last several turns). |

---