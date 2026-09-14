# Future Crash + LOOK 2.3.9

Versions:

- Future Crash + LOOK: 2.3.9
- LOOK: 4.3.9
- Future Crash: 1.1.10

## Model benchmark runtime fit

`lk ollama test` now separates two questions:

1. Can the model do LOOK work correctly?
2. Is it responsive enough to be pleasant interactively?

The table adds a runtime `FIT` column:

```text
EXCELLENT
GOOD
SLOW
POOR
```

The classification uses intentionally broad warm TTFT and generation-rate thresholds. It is a user-experience signal, not a hardware diagnosis.

A model with excellent tools/agent/exact results but pathological latency is therefore reported honestly, for example:

```text
gemma4:31b   42.53s   14.9   POOR   3/3   yes   yes
runtime note · capability may be excellent; runtime is pathological · inspect `lk ai stats` / `ollama ps`
```

Use `lk ai stats` for LOOK/Ollama telemetry and `ollama ps` for Ollama's current model residency/processor information.

The 2.3.8 shell namespace remains unchanged: canonical `lk ...`, permanent `lk*` fast commands, collision-aware optional short aliases, and native `fc`/`ls`/system executables left alone.
