# Future Crash + LOOK 2.1.2 — Shared inference lane

Versions:

- Future Crash + LOOK: 2.1.2
- LOOK: 4.1.2
- Future Crash: 1.1.8

## Purpose

2.1.2 coordinates model use without merging AI identities.

LO and Future Crash still have different system instructions, memories, personalities, permissions, and tools. Living AI now acts as the shared inference traffic coordinator underneath them.

## Priority contract

1. Explicit interactive work may start immediately.
2. Living AI will not start maintenance while an interactive Future Crash lease is active.
3. Automatic Future Crash ambient work only starts when:
   - no interactive lease is active,
   - Living AI is not already processing a background unit,
   - no queued LO background job, memory job, or skill-reflection job is waiting.
4. Once a scheduled Future Crash Thread begins, its repair/continuation passes may finish as the same admitted unit of work.

## Standalone behavior

Future Crash does not require LOOK or Living AI. If the broker socket is unavailable, its Oracle behaves exactly as before.

## Boundary

Coordination is resource scheduling only. It does not share:

- personality
- conversation memory
- long-term memory
- learned skills
- host permissions
- access profiles
- tool state
