# 6.1.0 — Tailcat Direct Transport

- Make browser endpoint management Fabric-wide: list, approve, and revoke from any reachable trusted node.
- Add Tailcat phase 1: direct certificate-pinned TLS Fabric transport on port 7443.
- Prefer Tailcat for paired peers and fall back to Tailscale when direct reachability is unavailable.
- Preserve the existing node authorization credential over both transports.
- Let existing 6.0 trust records learn Tailcat transport metadata from matching trusted peer identities without another re-pair.
- Add `lk fabric transport` diagnostics.
- Keep NAT traversal, relay, and browser remote reachability out of Tailcat phase 1.

# 6.0.0 — Fabric Authorization

- Enforce paired-node authorization on remotely reachable Fabric API routes.
- Mint reciprocal high-entropy peer credentials during pairing; keep public discovery/health/pairing routes minimal.
- Replace awkward copy/paste-first pairing with eight-digit one-use codes and `lk fabric pair NODE CODE`; keep QR transport optional.
- Add attempt limiting to pairing invitations.
- Add Signal Window 1.8.0 browser endpoint authorization with six-digit pending codes.
- Add `lk fabric endpoints`, `allow`, `revoke-endpoint`, and `endpoint-code`.
- Support allow-once, trust-device, revocation, one-use QR invitations, scoped endpoint credentials, and HttpOnly cookies.
- Preserve Tailscale as an optional transport rather than an identity/authorization provider.

# 5.9.0 — Fabric Identity

- Add a transport-independent Ed25519 identity to every Fabric node.
- Derive a stable `fcl-...` node ID and human-readable fingerprint from the public key.
- Add a local trust store with `lk fabric identity`, `lk fabric trust`, and `lk fabric untrust`.
- Add one-use, five-minute pairing invitations with strong short codes and `fcl://pair` URIs.
- Render a terminal QR code when optional `qrencode` is available; pairing itself has no QR dependency.
- Pairing exchanges and validates public identities over the currently reachable transport; Tailscale may carry the request but no longer defines Fabric identity.
- Keep trust non-enforcing for this migration release so existing Fabric nodes continue to interoperate; signed/scoped authorization is the next phase.

# 5.8.0 — Accountless Web Search

- Prefer Fabric/local SearXNG for generic web search; Ollama hosted search is optional fallback.
- Advertise `web.search` from nodes with a healthy local SearXNG edge.
- Route LO search through Fabric without requiring an Ollama account/API key.
- Rewrite README around the current architecture and reuse existing screenshots.
- Protect Dash on narrow terminal geometries.

## 5.7.2 — Find Retrieval Repair

- Fixed Unified Node query tokenization so Fabric file searches use real lexical terms instead of degrading into newest-file listings.
- Plain lexical misses now return zero results; unconstrained catalog listings remain available only for explicit metadata intents such as `recent` or `biggest`.
- `lk find` now opens an interactive paged result chooser on a TTY, with filtering, navigation, snippet preview, and path copy.
- Accepting a locally reachable result hands it to the normal LOOK file view, where existing preview/mark/copy/move/remove/LO actions apply. Remote/unmounted Fabric results remain safe and are never treated as local paths.

## 5.7.1 — Smart Resolver

- Preserves 5.7.0 Fabric Content Search and adds deterministic catalog-backed target resolution for open/preview/reveal.
- Adds quoted-phrase directory hints and ambiguity-safe resolution.

# 5.7.0 — Fabric Content Search

The ordinary-file catalog now has a deliberately boring second layer: bounded deterministic text extraction plus SQLite FTS5. `lk scan` still owns discovery, but changed supported documents are now text-indexed incrementally; unchanged documents are not re-read. No embeddings, OCR, model calls, or hashing are part of indexing.

Supported content sources are plain text/Markdown, source and common config formats, HTML, DOCX, EPUB, and text-bearing PDFs. HTML/script noise is stripped, DOCX/EPUB use their standard ZIP/XML/HTML containers, and PDF extraction uses the already-installed Poppler `pdftotext` edge. Files over 4 MiB are left metadata-only and extracted text is capped at 256 KiB per file.

`lk find` now combines filename/path matches with FTS5 content matches and shows a short evidence snippet. Natural queries such as `lk find "where was that thing I wrote about GDP countermeasure happiness"` work without embeddings. Fabric search remains data-local: every node searches its own SQLite database and returns only bounded matches/snippets, never its full text index.

This establishes the cheap content layer for later artifact identity, data-local job placement, and optional semantic search without making those expensive mechanisms prerequisites.

# 5.6.1 — File Catalog Concurrency Repair

- Fixed SQLite lock race between installer/background scan and manual `lk scan`.
- Added SQLite busy timeout, migration-only schema version writes, and single-crawler locking.
- Concurrent manual scans now report `scan already running` while searches remain available.

# 5.6.0 — Fabric File Catalog

LOOK now maintains a lightweight SQLite metadata catalog for ordinary files, extending the media-catalog lesson to the rest of the filesystem. `lk scan [ROOT]` records paths, names, extensions, sizes and modification times without reading or hashing file contents; a bare `lk scan` uses the home directory with conservative cache/build/hidden-directory exclusions. `lk catalog` reports local coverage and `lk find QUERY` accepts useful plain-language metadata terms such as `pdf`, `recent`, `yesterday`, and `largest`.

Each Unified Node publishes its local catalog through `/v1/files/catalog`; `/v1/files/fabric` unions currently reachable node catalogs. `lk find` prefers that Fabric union when the node is available and falls back to the local SQLite catalog in Island Mode. Paths remain node-owned metadata: cataloging never grants new filesystem access and never transfers file bytes.

Fresh installs seed the first home metadata scan in the background. Expensive identity, content extraction, FTS and semantic understanding remain deliberately deferred layers rather than costs paid during discovery.

# 5.5.0 — Media Endpoint Handoff

Signal media output routing is now explicit: browser playback is a local browser endpoint and never enters Fabric media-move dispatch, while node-to-node handoff uses the Fabric route. Cross-node queues are rewritten to range-capable source-node stream URLs so a Mac can play a 3090 library without sharing `/srv` paths or copying the track first. Signal uses stable endpoint buttons rather than an iOS native select picker, and node HTTP errors preserve their real diagnostic instead of collapsing to `Fabric media move unavailable`.

# 5.4.9 — Stable Safari Output Picker

- Keep Signal OUT selector DOM-stable while native Safari picker is active.
- Media polling continues observing state but cannot redraw the picker out from under iOS.
- Change commits normally; blur performs one reconciliation render.

# 5.4.8 — Media Output State Repair

- Replace competing Signal media-output state with one authoritative target: `browser` or `node:<id>`.
- Suspend media polling during browser handoff; polling observes state and never chooses the output.
- Avoid rebuilding the native iOS `<select>` during its `change` event while Safari dismisses the picker.
- Commit browser playback before stopping the source node; source-stop failure becomes a warning rather than rolling back into duplicate playback.
- Treat node playback availability as a capability (LOOK + mpv), not as the existence of an already-active local media session. Freshly upgraded Macs can therefore advertise as valid outputs before playing anything.
- Keep node option values namespaced so `This Device` and a Fabric node can never both represent the same selected value.

# 5.4.7 — Media Endpoint + Dash Input Hygiene

- Make Signal browser-output handoff transactional: **This Device / This iPhone** claims the card immediately while Safari starts playback, so background media polling cannot snap the selector back to the source node.
- Stream proxied media audio incrementally through Signal and remote Fabric nodes instead of buffering an entire track before Safari receives bytes.
- Keep browser playback failure reversible: the source node remains authoritative until browser audio starts, and the selector restores the source with a visible error if Safari rejects playback.
- Treat beacon/RGB/pulse records as renderer effects rather than RECENT semantic work in Dash.
- Consume ANSI cursor/mouse/scroll escape sequences as terminal input, preventing arrow-down (`ESC [ B`) and terminal gestures from becoming the `B` beacon hotkey.
- Rate-limit the Dash beacon hotkey so key repeat cannot launch overlapping diagnostic shows.
- Update help/docs/version surfaces and add endpoint/Dash regression coverage.

# 5.4.6 — Endpoint Media Cleanup

- Move Signal media output selection from the chat composer onto the active media card.
- Add ephemeral **This Device** / **This iPhone** browser audio playback without treating browsers as full Fabric compute nodes.
- Add range-capable Fabric media audio streaming and queue-index-preserving handoff between browser and node playback endpoints.
- Surface concrete output availability reasons such as `mpv missing` instead of unexplained disabled nodes.
- Promote `mpv` to a standard LOOK workstation dependency so fresh installs and upgrades automatically enable media playback on Macs and Linux nodes.
- Update Signal help, docs, release/version surfaces, and regression coverage.

# 5.4.5 — Node-Scoped Media Outputs

- Split Fabric media session meaning from node-specific playback output. Each reachable node advertises a default `media.playback` / queue / control endpoint.
- Add routed media state/control/play APIs and session handoff between nodes; moving output preserves queue/current index and stops the old playback worker only after the target accepts the session.
- Add Signal **OUT** chooser, per-node queue/player state, deterministic selected-node `play ...` routing, and shared controls against the selected output.
- Add `lk media outputs` and `lk media on NODE ...` deterministic operator surfaces.
- Fix iPhone camera prompt selection: `what am I looking at?` is real preselected composer text, so Return accepts it and typing replaces it.
- Update help, completion, man page, command/reference docs, installer/version surfaces, and tests.

# 5.4.4 — Signal Camera + Service-Safe Media

- Add Signal 1.4.0 camera/photo attachment from the chat input using the browser's native rear-camera capture surface.
- Treat camera photos as ordinary resources: Signal materializes bytes locally, LO selects the image path, and Fabric stages the image as an artifact for vision inference.
- Keep the 524288-byte Fabric ingress boundary intact; camera image bytes are not embedded in work packets.
- Make LOOK mpv discovery robust under systemd/launchd service PATHs, including Linuxbrew, Homebrew, and normal system locations.
- Preserve the real media edge diagnostic in LO/Signal when playback fails instead of returning only `MEDIA PLAY FAILED`.
- Add defensive PATH configuration to the Signal service edge while retaining runtime discovery/fallback.
- Update Signal help, install banners, release/version surfaces, documentation, and tests.

# 5.4.3 — Signal Media Card

- Add Signal 1.3.0 live media card over LOOK's canonical MediaSession.
- Auto-discover playback started from any local LOOK/LO surface; browser ownership is never required.
- Add previous, play/pause, next, stop, expandable queue, and exact queue-item jump controls.
- Add renderer-neutral `lk media state` JSON snapshot and deterministic `lk media jump INDEX`.
- Keep mpv/LOOK as the sole playback owner; dismissing or closing Signal leaves playback untouched.
- Update help, command grammar, man page, Signal docs, completions, release history, installer banners, and version surfaces.

# 5.4.2 — Island Resilience + Workstation Editor

- Add `lk doctor island`, a loopback-only single-node autonomy audit for local LOOK, Ollama, memory, media, and optional OpenJev.
- Codify the one-node Fabric invariant: remote workers increase capability but are not a prerequisite for local LOOK/LO operation.
- Repair Future Crash Ask/Workstation editing so the logical input buffer and cursor are authoritative; every frame redraws the fixed-width editor viewport, eliminating stale glyphs and phantom right-column deletion.
- Document Backspace/Delete and left/right/Home/End cursor behavior in Future Crash help.
- Synchronize README, command reference, command grammar, man page, completions, architecture, release history, and installer/version surfaces.

# 5.4.0 — Canonical Decision Worker

- Promote the Decision Plane into normal Fabric cognition: deterministic fast paths, learned judgment, human clarification, and graceful fallbacks share one policy path.
- OpenJev is now an optional first-class decision worker with config, health, systemd lifecycle, installer adoption/install modes, capability discovery, and Local Labs server controls.
- LO media ambiguity can use OpenJev live while exact controls remain deterministic and instantaneous.
- Decision telemetry records probability distribution, top-two margin, confidence, latency, policy disposition, and provider failures for later evaluation.
- Dash adds cognition/decision visibility and semantic JUDGE / ASK / ACT feedback without turning uncertainty into a blocking UI.
- Missing, disabled, or failed OpenJev degrades to existing deterministic/LLM behavior; it is never a hard dependency.

# 5.3.2 — Decision Interaction

- Make `lk fabric ask` interactive in a TTY while remaining renderer-neutral: terminal, Signal, or another Fabric surface may answer the same pending decision.
- Poll while waiting so a Signal answer immediately releases the originating terminal; bare Enter leaves the decision pending instead of blocking.
- Add the obvious `lk play TARGET` shorthand and route it directly to the existing LOOK media session instead of falling through to the file renderer.
- Keep decision deadlines/fallback policy authoritative in Fabric; the terminal is only another optional consumer.

# 5.3.0 — Decision Plane

- Human clarification becomes a renderer-neutral Fabric object instead of a blocking terminal prompt.
- Decisions carry confidence, consequence, reversibility, deadline, preferred choice, and timeout policy.
- Power/Unsafe can auto-continue only low-consequence reversible work; Workspace/Conservative defer; consequential/irreversible work requires explicit confirmation and cancels on silence.
- Pending decisions aggregate across trusted nodes and can be answered from terminal or Signal.
- Continuation work re-enters the normal Fabric Work Packet authorization path; UI surfaces never execute work directly.
- Adds an optional OpenJev-compatible shadow adapter at `/v1/decisions/shadow` with no model/runtime dependency.
- Signal 1.2.0 adds a compact decision card with countdown and one-tap answers.

# 5.2.19 — Media Session Reliability

- Reuse the LOOK-owned mpv process for ordinary play requests instead of spawning overlapping players.
- Add deterministic first/last/first-on-album media controls for LO.
- Make selector queue mutation canonical-only so Q returns immediately without stream resolution or player I/O.
- Preserve MediaSession as the owner of queue state; mpv remains a playback worker.

# 5.2.18 — LO Media Tools + LOOK Media Filter

- Added first-class LO media tools: `media_search`, `media_play`, `media_queue`, and `media_control`.
- Added conservative deterministic preflight for narrow local media commands so `lo play Talking Heads` cannot drift into web search.
- Kept explicit online/video requests on the existing web-resource path.
- Reworked `lk media find` around LOOK filter semantics with immediate filtering and Tab multi-select.
- Added contextual uppercase selector actions: play, queue, queue visible matches, info, save playlist, and clear selection.
- Kept exact catalog/artifact rows underneath human-readable labels.
- Added regression coverage for LO media routing and selector semantics.

# 5.2.17 — Fabric Media Catalog + LOOK Selector

- Replace the awkward print-then-retype media search flow with a LOOK-native interactive selector: Enter plays, Space appends to the canonical queue, `A` plays the visible match set, `/` refines the filter, and `I` shows lightweight identity/format detail. Non-interactive output remains plain text.
- Add a Fabric-wide media catalog assembled from currently reachable trusted nodes. `lk media fabric` reports logical items, physical scanned locations, per-node counts, and progressive SHA identification state.
- Add generic artifact catalog endpoints (`/v1/artifacts` and `/v1/artifacts/fabric`) so SHA-addressed files have a discoverable Fabric registry beyond the media demo.
- Add progressive media identity. Fast scans still avoid hashing; `lk media identify QUERY|PATH|--all` promotes discovered files to SHA-256 artifacts. Bulk `--all` is deliberately node-local, while a selected remote item can be identified on demand by its source node.
- Preserve SHA identity across rescans only when size and mtime still match; changed files fall back to discovered/unidentified state rather than retaining stale content identity.
- Merge duplicate online copies by SHA while preserving location lists and preferring a local copy for playback. Unidentified look-alikes never deduplicate merely by filename.
- Feed zsh media completion from the same online catalog, bounded to a small candidate set of artists, albums, and titles.
- Keep queue/session ownership in LOOK and decoding in mpv; no recommendation engine, artwork system, ratings database, or fixed media-root worldview was added.

# 5.2.16 — Media Sessions + Library Queue

- Add dependency-free `look/media_core.py`: the queue/library model is pure logic; playback, filesystem, terminal, and Fabric transport remain edges.
- Add fast `lk media scan ROOT` indexing with no full-file hashing or decoding, plus `library`, `find`, `artists`, and `albums` views. No media root or storage layout is hard-coded.
- Add persistent LOOK-owned `MediaSession` queues, directory/album/artist/query playback, `--shuffle`, queue inspection, repeat-all, and clear/restart behavior.
- Keep mpv as the optional dumb playback engine. LOOK mirrors its canonical queue into an M3U8 runtime edge and reconciles live playlist position back into MediaSession.
- Add saved queue playlists (`save`, `load`, `playlists`, and `playlist ...`) that exclude player PID/socket/runtime state so they survive ordinary restarts and remain repairable after storage moves.
- Add `lk player`, a tiny live terminal miniplayer with progress, queue position, seek, previous/next, repeat, stop, and close-without-stopping controls.
- Preserve generic artifact transport. Same-node queues may use direct local file URIs; `lk media stream` explicitly exercises Fabric registration/range streaming, and remote digest entries still use Fabric streams.

# 5.2.15 — Streaming Artifacts + Media Proof

- Generalize Fabric artifacts beyond small in-memory blobs: existing large files can be registered in place by SHA-256 without copying them into the Fabric state directory. Physical path remains a node-local location, while the artifact digest is the logical identity.
- Add HTTP `HEAD` and single-range `GET` support (`Accept-Ranges`, `206`, `Content-Range`) for artifacts so large audio/video/data files can seek and stream without whole-file downloads or RAM buffering.
- File-backed artifacts fail closed if their observed size/mtime changes after registration; re-registering establishes a new content identity/location record. Public artifact metadata never exposes the node-local source path.
- Nodes now advertise `artifact.read`, `artifact.range`, and `artifact.stream` as generic capabilities. Media is the proof case, not a special storage architecture.
- Extend `fcl-node` with `artifact-add` and `artifact` inspection/URL commands, including peer stream URL resolution.
- Extend `lk media`: existing no-argument transport controls remain compatible, while `lk media add PATH`, `lk media play PATH`, `lk media play @NODE sha256:DIGEST`, and `lk media info` exercise Fabric artifact transport.
- Prefer optional `mpv` as the dumb playback edge. LOOK launches it with a local JSON IPC socket so the existing play/pause/next/previous/stop controls can operate the LOOK-owned stream session; VLC/system playback remains a fallback.
- Do not introduce a media-library database, fixed `/mnt/music` path, transcoder, codec stack, or storage layout. The coming 3090 storage audit can reorganize physical disks without changing the artifact/stream contract.

# 5.2.14 — Shared Fabric UI Model

- Added `core/ui_model.py`: a renderer-neutral presentation model for nodes, capabilities, jobs, services, recent events, and actions.
- Dash controls now render from the shared action registry instead of duplicating their semantics in terminal code.
- Dash full/wide views expose a compact capability summary, so the UI begins reflecting Fabric as a graph of capabilities rather than only machines/services.
- Added `GET /v1/ui/state`, a stable `fabric-ui-v1` JSON surface for Signal and future renderers; no HTML, ANSI, or terminal assumptions leak into the model.
- This is an incremental mainline change, not a UI rewrite: existing Dash/LOOK/Future Crash behavior and hotkeys remain intact.

# 5.2.13 — Vision Runtime Fix

- Fix vision artifact hydration on the Unified Node by importing Python's `base64` module at runtime before converting artifact bytes into Ollama image payloads.
- Add a regression test that exercises the runtime symbol used by the artifact-to-vision bridge, preventing this NameError from returning.
- No scheduler, artifact format, packet-size, or model-curation behavior changed.

# 5.2.12 — Interactive Reliability

- Keep `lk dash` alive when Ctrl-C is used to leave Watch. The LOOK launcher now lets the dashboard/watch child own SIGINT and continues waiting instead of surfacing a parent `KeyboardInterrupt` traceback.
- Treat inference HTTP 409 `worker busy` as temporary capacity pressure for interactive work. Routing still tries distinct workers first, then uses a short bounded grace window with fresh placement snapshots before declaring the Fabric unavailable. Background work continues to fail fast.
- Make streaming inference lease cleanup exception-safe across the entire post-acquire path, including model discovery and vision-artifact hydration, so a pre-stream failure cannot leave a ghost BUSY worker behind.
- Add regression coverage for bounded busy retry, dashboard Ctrl-C ownership, and final streaming-lease cleanup.

# 5.2.11 — Live Tail + Vision Artifacts

- Move LO vision pixels out of Fabric work packets. The selected worker receives image data through the content-addressed artifact endpoint, while the inference packet carries only SHA-256 artifact references; the worker rehydrates images only at its Ollama edge.
- Preserve the 512 KiB Fabric packet guard instead of hiding oversized vision requests by raising it.
- Make `lk fabric watch` join the current event tail on first contact rather than starting at sequence zero and draining an overnight backlog. A live watch only follows cursor events accumulated during that watch session.
- Bound the operational Fabric event ledger to seven days / 20,000 rows, pruned incrementally, so disconnected clients cannot create permanent replay debt or an ever-growing event database.
- Keep explicit event history available through the retained ledger while making live-vs-history semantics distinct.

# 5.2.10 — Isolated Model Qualification

- Make `lk ollama test --all` a comparable per-node sweep: one target model resident at a time, canonical 4096 context, one discarded stabilization pass, then three identical warm samples with median TTFT/generation rate.
- Report cold model load time separately from warm TTFT, plus Ollama's achieved GPU residency percentage when available.
- Add a local benchmark guard so the background qualifier, adaptive curator, and Fabric job worker cannot silently alter Ollama residency during a benchmark sweep. The guard has a TTL and is released in `finally`.
- Restore the exact pre-sweep resident model names instead of loading only the selected/default model afterward.
- Keep enable/disable policy node-local: each node's curator now reports its eligible and disabled model sets explicitly, making machine-specific curation visible.
- Persist benchmark scope, load time, GPU share, and raw warm samples alongside capability evidence for later platform/model policy decisions.

# 5.2.9 — Ollama Command Dispatch Fix

- Fixed `lk ollama curate ...` and `lk ollama warm ...` being mistaken for long-form LO chat prompts before the Ollama subcommand dispatcher could see them.
- Added a release regression test covering every first-class Ollama management subcommand that must bypass chat dispatch.
- No curator policy, model residency, benchmark, or Fabric scheduling behavior changed.

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
