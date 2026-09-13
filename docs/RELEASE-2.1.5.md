# Future Crash + LOOK 2.1.5 — Living AI version handshake

Versions:

- Future Crash + LOOK: 2.1.5
- LOOK: 4.1.5
- Future Crash: 1.1.8

## Bug

Living AI is a resident process and imports LOOK once when it starts.

Previously, installing a newer LOOK version updated files on disk but did not invalidate an already-running broker. That broker could continue processing new memory jobs with old extraction/reinforcement code. The queue would drain normally, making the stale runtime difficult to detect.

## Fix

Broker status now returns the imported LOOK core version. Before LOOK wakes background work, it compares:

```text
running broker core
vs
installed LOOK VERSION
```

If they differ, LOOK stops the old broker, launches the installed broker, verifies the new version, and only then wakes background work.

`lk ai status` now includes:

```text
core        4.1.5
```

A legacy/stale broker is explicitly visible rather than silently trusted.
