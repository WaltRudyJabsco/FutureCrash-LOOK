# Living AI Architecture

`look_ai.py` is a local coordinator, not another model server. Ollama remains the inference server.

The broker owns scheduling and queue drainage. It does not own filesystem rendering, file mutation semantics, or terminal UI.

## Priority

1. **Foreground** — interactive LO establishes a short foreground lease. The broker will not start new background inference while that lease is fresh.
2. **User background** — explicit `lo bg` work.
3. **Maintenance** — memory consolidation and skill reflection.

Maintenance is deliberately incremental so foreground work can take priority between calls.

## Durability

The Unix socket is disposable. The queues are durable. A broker restart scans the existing job, memory, and skill-feedback directories and continues.

## No autonomous drift

Idle compute is used only when new evidence or queued work exists. A completed memory state does not recursively become evidence for another rewrite.

## Failure and retry

Ollama reachability is checked at the durable memory boundary. A failed endpoint leaves the queued exchange untouched. Maintenance failure introduces a 30-second retry backoff; an explicit wake or fresh work may reset the backoff.


## Release status

Living AI is distribution-ready in Future Crash + LOOK 2.1.1 / LOOK 4.1.1. `lk ai status` treats running and stopped as valid inspection states.


## Shared inference lane

Future Crash 1.1.8 is an optional client of the Living AI scheduler.

This does not make Future Crash and LO one assistant. Future Crash retains its Oracle personality and private memory. LO retains LOOK personality selection, Living Memory, learned skills, and access profiles.

Living AI only arbitrates idle inference capacity:

```text
interactive LO / Future Crash
          ↓
      shared lane
          ↓
        Ollama

idle lane:
LO background → memory → skills → Future Crash ambient/thread work
```

Future Crash registers per-process leases under the LOOK runtime state while an explicit Oracle request is active. Automatic Future Crash work asks permission before entering the background lane.

If the broker is unavailable, Future Crash falls back to standalone direct-Ollama behavior.
