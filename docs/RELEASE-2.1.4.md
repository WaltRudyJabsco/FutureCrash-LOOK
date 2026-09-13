# Future Crash + LOOK 2.1.4 — Living Memory reinforcement correctness

Versions:

- Future Crash + LOOK: 2.1.4
- LOOK: 4.1.4
- Future Crash: 1.1.8

This release fixes candidate reinforcement without changing the broker or scheduler.

The regression case is Sapphire:

```text
We're using sapphire as the codename for the current LOOK memory test.
We decided sapphire will remain the codename for this current LOOK memory test.
We're continuing to use sapphire as the LOOK memory-test codename.
```

Expected lifecycle:

```text
first evidence  → candidate / USES 1
second evidence → same candidate / USES 2 / importance +8
third evidence  → same candidate / USES 3 / promotion
                → LONG-TERM
                → active Sapphire candidate retired
```

If the model extractor returns NONE on a later paraphrase, a strong distinctive-token overlap with an existing active candidate may still count as reinforcement.

`lk memory` now persists cumulative extraction and consolidation receipts.
