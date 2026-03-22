# Ethical risks (short)

## 1. Wrong memory, said confidently

If retrieval picks the wrong snippet or the model states something too definitely, trust erodes fast — worse in a mental health-adjacent product.

What I did here: keep memories short, keep openers soft (“last time we touched on…” not “the system records that you…”). No diagnostic language in the extraction prompt.

What I’d still want: human review of prompt outputs on edge cases, and a way for users to flag “that wasn’t right”.

## 2. Bad timing

Surfacing heavy stuff right after someone’s raw, or in a push notification, can land wrong.

What I did: notification copy is intentionally vague; rules bias toward gentle check-ins. Openers are instructed not to sound like a database readout.

What I’d still want: explicit “do not notify” states, rate limits, and clinical input on what never goes in a push.

## 3. Data exposure

Memories are sensitive. Any leak is worse than leaking a shopping cart.

What I did: filter vectors by user, store summaries not full transcripts in Qdrant, keep the schema small.

What I’d still want: encryption at rest, access logs, retention limits, and a real deletion story — none of that is fully built in this repo.

---

**Before shipping anything real:** run this past clinical + legal. Questions I’d ask them: which memory types are auto-surfaceable, when to suppress notifications, how to handle minors or crisis language, and what audit trail they need.
