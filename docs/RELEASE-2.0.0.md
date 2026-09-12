# Future Crash + LOOK 2.0.0

## Portable identity

2.0 separates LOOK into four state layers: program, profile, machine, and runtime.

The **profile** is the portable part of the evolving local AI: memory, recent conversational continuity, core customization, skills, personalities, access/personality/thinking preferences, preferred model name, and feedback settings.

Use:

```text
lk profile
lk profile backup ~/Documents/LOOK
lk profile export
lk profile restore look-profile-YYYYMMDD-HHMMSS.zip
```

A backup destination is remembered. Backups are timestamped snapshots with configurable retention. Export creates a single migration ZIP. Restore validates schema and paths, then creates a local safety snapshot before replacing the portable live state.

Secrets, undo/trash, jobs/events, memory queues/locks, PIDs, generated caches, and machine-specific Ollama host configuration do not travel.

## Skills promotion

`lk skills export` writes only locally learned skills. That file can be reviewed and deliberately folded into a future built-in skills pack without treating a personal profile as distribution source code.

## Terminal expression

`lk feedback` controls the shared finite feedback layer.

```text
lk feedback
lk feedback motion off|subtle|normal
lk feedback sound on|off
lk sound
lk feedback demo
```

Sound defaults off. Motion defaults subtle. Feedback is disabled automatically when stdout is not a TTY.

LOOK is 4.0.0. Future Crash remains 1.1.7.
