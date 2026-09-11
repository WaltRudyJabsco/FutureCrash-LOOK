# 1.1.4 — Conversational continuity + nesting guard

## Memory
- Candidate capture is intentionally less conservative.
- Preferences, favorites, habits, project decisions/state, unresolved tasks, and explicit memory requests are normally remembered.
- Importance guidance now distinguishes recent continuity from durable preference.
- Explicit phrases such as `remember this`, `this is important`, `one of my favorites`, `I really like`, and `I prefer` receive a deterministic fallback when the semantic worker returns `NONE`.
- Existing decay, sanitation, 20-candidate cap, 8-memory attention cap, and long-term summary behavior are unchanged.

## Future Crash
- Prevents accidental recursive Future Crash nesting.
- Shells entered from Future Crash inherit `FUTURE_CRASH_ACTIVE=1`.
- `fc`, `rst`, and `future-crash` refuse to launch another normal instance while already inside one.
- `future-crash --nested` remains an explicit escape hatch.
