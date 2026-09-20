# Future Crash + LOOK 5.2.0 — Personas + Fabric Memory

## One brain path, many faces

- Future Crash Ask and X Workstation now use LOOK's canonical native LO/Fabric engine for normal conversation.
- Oracle is now a persona, not a model or host. The conductor may route Oracle turns to any suitable Fabric worker.
- Future Crash inherits trusted temporal grounding, canonical tool edges, LO memory retrieval, and canonical visible-text extraction.
- User/session access profile remains independent from personality. Oracle does not gain power merely by being Oracle.
- The Future Crash header now reports `ORACLE · FABRIC:AUTO · <PROFILE>` rather than pretending Oracle is one local model.

## Persona registry

- Added `oracle` and `pirate` to the existing `lo`, `robot`, `max`, and `philosopher` registry.
- Native `lo_engine.chat_once(..., persona=...)` supports a per-call persona override without changing the user's saved default.

## Fabric Memory v1

- Added `core/memory_store.py`: small JSON-backed scoped memory.
- Scopes: `shared`, `persona:<name>`, and non-replicating `node:<name>`.
- Unified Node exposes `/v1/memory` for add/merge/sync.
- Explicit peer sync is bounded and last-write-wins; node-local memories never replicate.
- LOOK injects relevant shared/persona/node memory alongside its existing durable local memory.
- New commands: `lk memory fabric`, `shared`, `persona`, `local`, `add-shared`, `add-persona`, `add-local`, and `sync`.

## Compatibility

- Existing LO memory remains intact.
- Existing Future Crash compact local memory remains intact and is supplied as Oracle-local context.
- Ambient, fortune, threads, and Signal compilation keep their specialized lightweight paths.
