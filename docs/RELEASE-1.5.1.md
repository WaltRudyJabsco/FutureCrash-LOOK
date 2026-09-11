# 1.5.1 — Future Crash final-only micro-generation

Versions:
- Future Crash + LOOK 1.5.1
- LOOK 3.8.0
- Future Crash 1.0.1

## Fixed
- Fortunes no longer display model reasoning.
- Oracle/ambient observations no longer display model reasoning.
- Handles normal `<think>...</think>`, structured Ollama `thinking`, and orphaned `</think>` template output.
- All Future Crash model output now passes through one shared final-answer extractor.

## Personality boundary
- Adds `future-crash/personality.md`.
- Future Crash keeps its own stable signal-field/workstation personality.
- LO's selectable personality does not leak into Future Crash.
