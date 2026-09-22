# Architecture

Future Crash and LOOK are one distributed environment with two modules.

- LOOK owns shell/navigation/system/file/AI tooling.
- Future Crash owns the ambient workstation/front-end experience.
- The installer owns composition.

Public commands:
- `future-crash` / `rst` / `fcr` — front end
- `lk` / `lo` — underlying terminal tools

Future Crash's launcher reads LOOK's selected Ollama model and host, so there is one AI configuration rather than two competing configurations.

## Portable intelligence

LO's persistent intelligence is intentionally file-shaped:

```text
core.md
skills.md
ollama_memory.json
```

Application versioning and intelligence-data versioning are separate.

- Memory has a schema version for migration.
- Skills has a schema version plus a Bundled craft-pack version.
- Bundled skills can be replaced independently.
- Learned skills remain local and survive Bundled updates.

This lets LOOK stabilize while reviewed assistant craft continues to evolve without inventing a skills package manager or database.


## LOOK 2.0 state boundary

LOOK separates versioned program material from portable profile identity, machine-local trust/configuration, and disposable runtime state. See `STATE-ARCHITECTURE.md` and `PROFILE.md`.

This boundary is also the long-term service contract: shell, filer, Future Crash, and future resident brokers may exchange jobs/events, while durable intelligence remains profile state.


## Shared inference coordination (2.1.2)

Living AI coordinates access to inference capacity across independent clients without merging their identities.

Future Crash is an optional client. Explicit Ask/Workstation operations register a per-process interactive lease. Automatic Future Crash work requests admission to the idle background lane. LOOK's own foreground lease, queued LO jobs, Living Memory, and skill reflection retain precedence over ambient Future Crash inference.

The coordination boundary is intentionally below personality, memory, permissions, and tools:

```text
Future Crash Oracle ─┐
                     ├─ Living AI inference lane ─ Ollama
LO / LOOK ───────────┘

identity/memory/tool state remain separate above the lane
```

If Living AI is unavailable, Future Crash remains a direct Ollama client.

## Single-node invariant

A Fabric containing one machine is a complete Fabric, not an error state. LOOK must retain deterministic tools, local files, local memory, local media, and any locally available inference when remote nodes, Tailscale, or the Internet disappear. Remote workers are capability expansion. `lk doctor island` is the release-facing diagnostic for this invariant and intentionally probes loopback/local resources only.

The cognition fallback order is deterministic rules, local decision worker when present, local generative model when appropriate, remote Fabric capability when reachable, then human clarification or a clear limitation. Tasks already known to require unavailable large capabilities should fail gracefully rather than forcing a small local model through futile work.
