# 1.2.1 — Durable memory promotion + long-term pruning

- LO no longer falsely claims explicit memory requests are session-only.
- Explicit durable phrases trigger immediate long-term-summary promotion.
- Durable candidate importance is raised to at least 90.
- Obvious duplicate candidates consolidate before summary promotion.
- Long-term summary is periodically rebuilt every 12 maintenance cycles.
- Summary maintenance is capped at 180 words and may forget stale, redundant, superseded, or low-value facts.
- Candidate decay/reinforcement and skills are unchanged.

Versions:
- Future Crash + LOOK 1.2.1
- LOOK 3.5.1
- Future Crash 1.0.0
