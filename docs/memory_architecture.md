# Memory design (MVP)

## Stored shape

Each row in Qdrant is basically:

```text
user_id, session_id, memory_text, memory_type, importance, session_date
```

`memory_type` is one of: theme, breakthrough, commitment, concern. Nothing fancy — just enough structure that prompts don’t turn into soup.

`memory_text` is what gets embedded. I deliberately did **not** dump full transcripts into the vector DB; the JSON files stay the source of truth for that.

## Why not more fields?

This was a time-boxed exercise. A fatter schema (entities, confidence, clinician tags, etc.) is easy to imagine but wasn’t worth the overhead here. Same for storing raw dialogue in Qdrant — bigger privacy surface and harder to reason about at review time.

## Retrieval

OpenAI embeddings (`text-embedding-3-small`) + cosine search in Qdrant, filtered on `user_id` so you can’t accidentally pull someone else’s memories in a multi-tenant world. The LLM steps (extract memories, write openers, Gradio replies) use DeepSeek’s chat API first, with OpenAI chat as a fallback if the call fails.

Flow: build a query string (from `current_context` or a generic fallback) → embed → top-k → pass snippets into the opener prompt.

## What I’m *not* trying to store

- Diagnoses or “you have X” style labels  
- Full verbatim transcripts as the searchable blob  
- Random PII unless the model sneaks it into a summary (prompt asks it not to)

## Messy data

Sample sessions don’t all have `clinical_flags`. Pydantic defaults those to `[]`. Days since last session is computed from `last_session_at` instead of trusting a static number in the profile. Closing “mood” for rules is inferred from a few keywords in the closing tone string — crude but works for the demo.

## User control (idea vs implementation)

Profile JSON already has privacy-ish flags. This codebase doesn’t enforce them end-to-end yet; in a real product you’d gate ingest/retrieve on consent and add delete + retention jobs.
