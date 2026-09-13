# Future Crash + LOOK 2.1.3 — Living Memory observability

Versions:

- Future Crash + LOOK: 2.1.3
- LOOK: 4.1.3
- Future Crash: 1.1.8

## Why

A healthy Living AI broker could drain the memory queue while candidate memory appeared frozen. The reason was subtle: RECENT is committed directly, but semantic memory depends on a background extractor. If that extractor repeatedly returned `NONE`, the queue correctly returned to zero while no new candidate evidence appeared.

2.1.3 makes that state visible and less brittle.

## Evidence paths

Memory extraction now runs in this order:

1. model semantic extraction;
2. deterministic obvious-evidence fallback for clearly stated preferences, durable project state, conventions, and explicit memory language;
3. explicit-memory fallback.

The deterministic path is deliberately conservative. It does not try to infer personality or facts from ordinary chatter.

## Diagnostics

`lk memory` now reports:

```text
extraction · candidate:model just now · 4/9 candidate · 5 none
```

or:

```text
extraction · none 2 minutes ago · 4/10 candidate · 6 none
```

This separates three conditions that previously looked identical:

- exchange was never processed;
- exchange was processed and judged non-memory;
- exchange produced candidate evidence.

Any recorded worker error is also shown directly.
