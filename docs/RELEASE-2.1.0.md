# Future Crash + LOOK 2.1.0 — Living AI

LOOK now has a resident local AI coordinator rather than a collection of unrelated one-shot workers.

```text
shell / LOOK / Future Crash / LO
              │
              ▼
       ~/.local/share/look/ai.sock
              │
              ▼
          look_ai.py
      P0 foreground lease
      P1 explicit background jobs
      P2 memory + skill maintenance
              │
              ▼
            Ollama
       local or remote 3090
```

The socket is intentionally only the fast coordination path. Jobs, memory work, skill feedback, and events remain durable files, so pending work survives broker crashes/restarts.

## Living Memory

Recent conversation remains literal continuity and stores both sides of an exchange. Semantic candidates now reinforce by meaning rather than exact wording. Forgetting is based on elapsed time rather than chat volume. Repeated/durable evidence triggers long-term rewriting immediately; candidates represented in long-term leave the active pool.

Background cognition stops when there is no new evidence. LOOK never repeatedly rewrites memory merely because the GPU is idle.

## Control

```text
lk ai
lk ai start
lk ai stop
lk ai wake
```

LOOK is 4.1.0. Future Crash remains 1.1.7.

## Failure behavior

The broker does not equate “the model call failed softly” with “memory work completed.” It proves the configured Ollama endpoint is reachable before consuming a durable memory job. Failed housekeeping remains queued, records the worker error, and uses retry backoff.
