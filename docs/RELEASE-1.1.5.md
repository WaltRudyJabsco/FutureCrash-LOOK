# 1.1.5 — Conversation-first LO + self-learning craft

## Conversation
- Casual conversation/general knowledge no longer triggers workspace inspection merely because tools exist.
- Relevant memories are used naturally; importance scores are not surfaced unless requested.
- `lo` is now `noglob lk o`, making `?`, `*`, and bracket glob characters safe in one-shot prompts.
- Unmatched shell quotes remain a Zsh parsing limitation; interactive `lo` is the unrestricted prose path.

## Memory
- User-memory extraction is explicitly grounded in what the user said or clearly confirmed.
- Assistant suggestions are not promoted into user preferences from acknowledgements such as `nice`.

## Skills
- LO can autonomously learn rare, generalized assistant craft into `skills.md`.
- Automatic learning is disabled in Conservative and enabled in Workspace/Power/Unsafe.
- Skill output must be exactly `NONE` or `SKILL|lesson` and is sanitized, deduplicated, capped at 24, inspectable, editable, and reversible.
- Adds `lk skills add`, `lk skills forget`, and `lk skills clear-learned`.
