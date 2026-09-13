# Future Crash + LOOK 2.3.0 — Living Memory compiler

Versions:

- Future Crash + LOOK: 2.3.0
- LOOK: 4.3.0
- Future Crash: 1.1.10

## Mental model

Living Memory is no longer one summary plus a small frozen candidate list.

```text
conversation
    ↓
candidate evidence
    ↓
reinforcement / contradiction / decay / competition
    ↓
durable atomic memories
    ↓
domain summaries
    ↓
tiny core routing summary
    ↓
relevant retrieval into the current prompt
```

Candidates are intentionally cheap hypotheses. Long-term durable memory is harder to earn.

## Domains

Durable atoms are classified into:

- PERSONAL — interests, favorites, tastes
- PREFERENCES — reusable choices and conventions
- PROJECTS — durable project decisions/context
- STYLE — interaction and working-style preferences
- GENERAL — useful durable facts that do not fit another domain

Machine/runtime facts such as the current GPU, current LOOK version, current Ollama endpoint, cwd, or current host belong to deterministic system state and are excluded from autobiographical memory.

## Context budget

The on-disk durable store may contain up to 240 atomic memories without putting them all in the prompt.

Normal retrieval injects only:

- one compact core summary;
- up to two relevant domain summaries;
- up to six relevant durable atoms;
- up to four relevant candidate memories.

This makes storage generous while attention remains intentionally small.

## Background compiler

The resident Living AI broker may use otherwise-idle cycles to recompile memory no more than once every six hours.

The compiler is instructed to:

- preserve meaning while reducing tokens;
- merge redundancy aggressively;
- never broaden scope;
- preserve qualifiers and uncertainty;
- never invent causality or preference;
- remove machine/runtime facts from user memory.

Promotion triggers an immediate compile. Durable reinforcement can also invalidate summaries for recompilation.

Manual command:

```text
lk memory compact
```

## Migration

Schema-2 long-term summary prose is preserved as:

```text
LEGACY (inactive)
```

It remains inspectable but is not injected into LO context automatically. This avoids carrying forward old over-generalized wording such as converting a project-scoped preference into a universal preference.

## Diagnostics

`lk memory` now shows:

- core summary;
- compiled durable domains;
- top durable atoms;
- recent conversation;
- active candidates;
- extraction ratio;
- promotions;
- consolidations;
- candidate evictions;
- compiler age;
- background queue/broker state.

## Documentation audit

`lk help all`, `lk commands`, `lk settings`, and Zsh completion now reflect:

- access grants;
- undo list/skip;
- reveal;
- AI stats;
- thinking vs think-display;
- current filer arrows/Shift-Tab;
- terminal ownership states;
- Living Memory compiler commands and concepts.
