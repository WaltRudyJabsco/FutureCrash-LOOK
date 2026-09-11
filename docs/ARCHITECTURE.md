# Architecture

Future Crash and LOOK are one distributed environment with two modules.

- LOOK owns shell/navigation/system/file/AI tooling.
- Future Crash owns the ambient workstation/front-end experience.
- The installer owns composition.

Public commands:
- `future-crash` / `rst` / `fc` — front end
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
