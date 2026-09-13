# Future Crash + LOOK 2.1.6 — Living AI liveness hardening

Versions:

- Future Crash + LOOK: 2.1.6
- LOOK: 4.1.6
- Future Crash: 1.1.8

This release does not change memory semantics. It hardens the resident Living AI process.

A PID file is no longer accepted as proof that a broker exists. The broker's Unix socket must answer the status protocol. This prevents stale PID files or OS PID reuse from leaving durable work queued behind a nonexistent coordinator.

The broker also contains unexpected background exceptions rather than exiting, and records them in:

```text
~/.local/share/look/ai_errors.log
```

Finally, `lk memory` treats:

```text
memory queue > 0
living AI stopped
```

as a recoverable condition and attempts to start/wake processing immediately.
