# Future Crash + LOOK 2.6.1

A surgical Living Memory lifecycle update.

The intended hierarchy is now explicit:

```text
RECENT
  high fidelity, short lifetime, includes sidebars
      ↓
CANDIDATES
  cheap semantic hypotheses, permissive admission, reinforcement + decay
      ↓
DURABLE ATOMS
  earned stable facts/preferences
      ↓
DOMAIN SUMMARIES
  aggressively compressed meaning
      ↓
CORE SUMMARY
  tiny routing/user model
```

`sidebar`, `no need to remember this`, `just for now`, and similar language do **not** mean "ignore this turn." The exchange remains in RECENT normally. They mean "do not promote this into deep memory."

Candidate admission is deliberately somewhat noisy. Durable promotion remains conservative.

`lk memory` now exposes the metabolism:

```text
extraction · ... candidate · ... none · ... local
metabolism · merged N · promoted N · expired N · evicted N
compiler · consolidated N · last ...
```

Schema-2 legacy summary content is migrated into the current durable system when useful and the inactive legacy tier is retired.
