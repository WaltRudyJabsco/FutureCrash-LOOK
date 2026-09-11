# LO Memory + Self-Learning

Maximum useful intelligence from minimum machinery.

- Up to 20 candidate memories on disk.
- Up to 8 candidates in prompt attention.
- Importance 0–100.
- Unused memories decay by one per maintenance cycle.
- Retrieval is not reinforcement.
- Durable patterns compress into one long-term summary.
- User memory is separate from reusable assistant skills.
- core.md, skills.md and ollama_memory.json remain human-readable and editable.
- Old fixed-slot LOOK memory migrates automatically.

Self-learning is intentionally conservative: the skills layer is inspectable and seeded with reviewed craft. Automatic autonomous skill accumulation is not enabled yet; experience should prove that useful before more machinery is added.

## Persistence hygiene

Memory workers fail closed. Candidate output must be exactly `NONE` or `NN|memory text`.
Qwen/Ollama reasoning is stripped before persistence. Obvious meta-reasoning is rejected.
Invalid summary rewrites retain the previous clean summary. Known 1.1.0 contamination is
pruned automatically when memory loads.

Use `lk memory prune` for an explicit cleanup, or `lk memory clear-summary` to reset only
the long-term summary.

## Capture policy

Candidate memory is intentionally broader than long-term summary.

Substantive preferences, favorites, habits, project decisions, active state, unresolved tasks,
and explicit requests to remember are normally captured. Low-value continuity can enter with
moderate importance and decay naturally if it never matters again.

Explicit memory-language has a deterministic fallback so phrases such as "remember this",
"this is important", "one of my favorites", and "I prefer" cannot silently vanish merely
because the semantic worker returned `NONE`.

## Self-learning skills

After each substantive exchange, LO may ask a separate question: did this teach one reusable
assistant technique that would improve many future tasks?

The answer must be exactly `NONE` or `SKILL|general lesson`. User facts, project-specific
details, filenames, model names, and conversation summaries are rejected. Learned skills are
deduplicated and capped at 24.

Capability boundary:
- Conservative: never writes skills.
- Workspace: may learn assistant craft.
- Power: may learn assistant craft.
- Unsafe: may learn assistant craft.

Controls:
- `lk skills`
- `lk skills add TEXT`
- `lk skills forget TEXT`
- `lk skills clear-learned`
- `lk skills path`

This is self-improvement in an inspectable Markdown layer, not unrestricted rewriting of LO's core.
