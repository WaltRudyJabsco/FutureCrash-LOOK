# 5.2.8 — Adaptive Model Curator

- Replace the first resident-set concurrency probe with stabilized 4096-context, repeated median measurements and a physical sanity bound; impossible >N× results are no longer scored.
- Add an evidence-driven model curator that plans canonical resident sets from installed model size, local benchmark evidence, current non-Ollama GPU pressure, and platform memory budget.
- Add `lk ollama curate`, `lk ollama curate --apply`, and opt-in `lk ollama curate auto on|off`; automatic mode reserves a deep worker for deep interactive work and returns to a balanced medium+small set when idle.
- Add `lk ollama warm MODEL...` using the canonical 4096 context.
- Respect LOOK-disabled models during curation and keep large deep models alone when their footprint would otherwise force unhealthy mixed residency.
- Let Fabric routing use benchmark role evidence as a placement hint while preserving hard capability requirements, live latency, residency, load, and node availability.

# 5.2.7 — Model Roles + Resident Sets

- Replace opaque multi-model `R2` residency with compact identities such as `R[q3:8b,g3:1b]`.
- Extend manual model benchmarks with three deterministic reasoning probes and preserve raw role evidence instead of inventing one universal model score.
- Add `lk ollama test --resident-set` to compare sequential vs concurrent response of the models already warm in Ollama; it never cold-loads or evicts a model.
- Surface purpose evidence in `lk fabric models` and compact Dash model summaries.
- Reserve a physical right-edge gutter in full Dash so the PULSE column is not clipped by terminal last-cell behavior.

# 5.2.6 — Adaptive Dash Geometry

- Replace coarse height breakpoints with fit-first responsive layout selection.
- Add a landscape renderer that spends horizontal width to preserve node/model, jobs, trust, control, service, ingress, and RECENT evidence in short terminals.
- Let RECENT consume spare rows instead of leaving large blank regions in medium windows.
- Preserve the full diagnostic renderer whenever it physically fits; Mini remains an explicit operator mode, not an automatic fallback.
- Keep model qualification and benchmark evidence unchanged.

# 5.2.5 — Responsive Dash + Benchmark Evidence

- Make live Dash height-aware: full, condensed, and compact compositions fit the terminal rectangle without paging.
- Protect RECENT and controls as terminal height shrinks; secondary telemetry compresses first.
- Keep `lk dash --snapshot`/non-TTY rendering full for copyable diagnostics.
- Persist LOOK model benchmark evidence and advertise local results alongside lightweight background qualification.
- Extend `lk fabric models` with benchmark fit, tool, agent, and exact-response evidence.
- Preserve Mini, Beacon, Lights, semantic event colors, and non-blocking keyboard behavior.

# 5.2.4 — Model Observability

- Dash MODEL cells now distinguish configured model, residency, qualification freshness, and measured generation rate instead of an ambiguous `*`.
- `lk fabric models [NODE]` exposes resident/available state, tested/untested/stale/failed qualification, TTFT, generation speed, and exact READY compliance.
- Background qualification remains opportunistic: resident models only, 20 seconds idle, once per 24 hours, and preemptible by interactive work.

# 5.2.3 — Dash Polish

- RECENT uses the same semantic color vocabulary as ambient activity flashes.
- Mini Dash (`m`) provides a compact activity instrument for small terminal windows.
- Removed broken Freeze and redundant Activity Color hotkeys; ambient colors are normal Dash behavior.
- Beacon and Lights remain explicit Fabric-wide test/demo controls.
- Quiet events may remain visible in RECENT without flashing; stream/token noise stays suppressed.

# 5.2.2 — Ambient Fabric

- `lk dash` now uses brief, restrained whole-terminal color flashes as passive Fabric telemetry: blue dispatch, amber inference, cyan capability/memory work, green success, red failure/cancel, purple general/remote work.
- Activity colors are derived from canonical Fabric events; producers never emit terminal-color instructions. Repeated stream/chunk events are deliberately ignored so Dash does not strobe.
- `a` toggles activity colors without affecting the existing synchronized Beacon or Light Demo.
- RECENT is now explicitly `RECENT · OBSERVED BY THIS NODE` and labels each event LOCAL or REMOTE. Cross-day events show a weekday/time so stale activity cannot look current merely because the live clock is ticking.
- Added `docs/GREENFIELD_FORK.md`, preserving the post-5.2 counterfactual design work without changing production architecture: distinct LOOK/LO/Future Crash/Signal projects, heterogeneous workers beyond Ollama, dual-resident model experiments, ephemeral browser/WebGPU workers, small-model cognitive maintenance, provenance, Show Work, and ambient observability.
- No rename of Fabric in production. Naming remains an experimental-fork decision.

# 5.2.1 — Evidence Labels + Ask Flow

- Future Crash Ask and Workstation now surface the provenance emitted by LOOK's canonical engine.
- Sourced turns show the canonical edge/provider receipt; turns without a source receipt are explicitly labeled `MODEL · INFERRED`.
- Provenance describes evidence origin, not probability or confidence percentage.
- `lo_engine.chat_once()` now returns structured `receipts` and a canonical `provenance` summary for native interfaces.
- Future Crash Answer view is conversational again: begin typing to start the next Ask question; Ctrl-C is not required.
- Signal/compiler telemetry remains separate from conversation provenance.

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
