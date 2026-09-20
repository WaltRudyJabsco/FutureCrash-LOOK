## 5.1.6 — Conversation Channels

- Restores Future Crash Oracle/Workstation as a normal user ↔ Oracle conversation while Signal remains a visual sidecar.
- Normal ask/work prompts no longer embed the full Signal language; Signal grammar is used only by the dedicated compiler/repair passes.
- Signal receipts/context are no longer injected into ordinary Oracle conversation history. They remain available to the Signal compiler only.
- Explicit visual requests now complete the visible text answer first, then compile the Signal scene asynchronously from the request + finished answer.
- `SIGNAL UPDATED` / compile-failure receipts move to the transient status line instead of becoming assistant chat messages.
- Future Crash tolerates canonical Fabric text surfaced outside `message.content` before declaring an empty visible response.
- Future Crash 1.1.15; Future Crash + LOOK / Unified Node / ingress 5.1.6. LOOK remains 4.43.3; Signal Window remains 1.1.2.

## 5.1.5 — Control Plane Clarity

- Dashboard HTTP telemetry now distinguishes accepted TCP connections from parsed HTTP requests and completed requests, so ingress counts no longer look like unexplained request loss.
- Ingress metrics expose connections that never produced a valid HTTP request, early client disconnects, 60-second request rate, and per-endpoint totals.
- `lk dash` now shows `conn / req / done / active / no-http / early / rate` instead of the ambiguous accepted/completed pair.
- Adds `[f] freeze` to pause dashboard repaint/polling for inspection and copy/paste while the Fabric continues running normally.
- Keeps the transport unchanged: this release improves accounting and observability rather than tuning healthy socket behavior blindly.
- Future Crash + LOOK 5.1.5; Unified Node/ingress 5.1.5; LOOK remains 4.43.3; Signal Window remains 1.1.2.

## 5.1.4 — Weather Receipt Closure

- Weather continuations such as `how about Beaverton OR`, `what is the high and low today`, and `is that accurate?` are now recognized host-side when WEATHER is the active conversational topic.
- High/low follow-ups read `temperature_2m_max` / `temperature_2m_min` from one typed WEATHER receipt; LO no longer reconstructs daily extrema from conversational prose or adjacent temperatures.
- Accuracy challenges trigger an independent National Weather Service observation check when available, with both provider values and timestamps preserved rather than silently choosing one.
- WEATHER discourse state is derived only from recent user/assistant turns so transient system prompts cannot evict the active location.
- This closes the weather-specific correctness pass; the same typed-receipt/follow-up pattern is intended for other Fabric capabilities.
- Future Crash + LOOK 5.1.4; Unified Node 5.1.4; LOOK 4.43.3; Signal Window remains 1.1.2.

# Changelog

## 5.1.3 — Signal Scene Guard

- Rejects degenerate conversational Signal scenes such as a saturated full-canvas clear or one giant filled rectangle.
- Adds deterministic domain fallbacks: weather card, news card, greeting pulse, and a neutral micro-signal.
- Weather fallback extracts only numeric values already present in the trusted answer; it never invents missing conditions.
- Visual responses now report `scene_source`, `fallback_kind`, and `fallback_reason` so the activity tape reveals whether a scene came from the reflex model or a template.
- Keeps full-screen color fills reserved for the separate Fabric light-show layer.
- Signal Window 1.1.2; Unified Node 5.1.3; LOOK remains 4.43.2.

## 5.1.2 — Weather Edge
- WEATHER resolves location deterministically before inference: explicit place → recent explicit weather place in the browser/session → optional `LOOK_WEATHER_LOCATION` / `LO_WEATHER_LOCATION`.
- US state shorthand is canonicalized before Open-Meteo geocoding (`portland or` → `portland, Oregon`).
- Missing location is reported as a location question, not mislabeled as a failed WEATHER receipt.
- Existing fail-closed live receipts and bounded transient retry remain intact.

## 5.1.1 — Fabric Show Reliability
- Dashboard `b` and `l` now call the node daemon control plane instead of creating a dashboard-local show, so the same canonical broadcast reaches peer dashboards and attached Signal browsers.
- WEATHER preflight gets one bounded retry for transient failures because the edge is read-only and idempotent; mutation tools remain non-retrying by default.
- Keeps the 5.1 Signal-attached display and leased light-show architecture intact.

## 5.1.0 — Signal Gets the Signal

- Signal Window is now a Fabric-attached display: synchronized Fabric light shows reach desktop dashboards and mobile/iOS browser Signals through the local node.
- Added `lk fabric lights demo|rgb|pulse|christmas|disco|stop`; disco/christmas are pulse-derived leased shows that run until Ctrl-C and expire safely if the origin disappears.
- Signal-first visual policy: every successful browser exchange gets an asynchronous Signal scene attempt, with a tiny deterministic fallback instead of silent visual failure.
- Signal composition now sees the actual answer and source receipts rather than racing ahead from the user prompt alone.
- Signal-language requests are explicitly separated from Comfy image generation; generated image artifacts render inline in the browser, including mobile.
- Dashboard `l` triggers the longer synchronized light demo; `b` remains the short diagnostic beacon.

## 5.0.0 — Fabric Alive

- Adds `lk fabric beacon`: a synchronized pulse-scheduled RGB diagnostic that all open Fabric dashboards render together. Dashboard key `b` triggers the same demo locally.
- Beacon delivery is real control-plane traffic; nodes schedule presentation against the shared one-second Fabric pulse instead of animating on packet arrival.
- Adds a small patient/Bear-style waiting cadence to active LO inference without inventing fake progress states.
- Compacts deterministic weather-edge inference: once the trusted WEATHER receipt exists, the reflex model receives only temporal truth, the receipt, and the user's question instead of LO's full tool/context manual.
- Keeps credentials and external-tool semantics out of the beacon path; 5.0 remains a lightweight network proof, not a second orchestration system.
- Fixes dashboard/event-tail staleness: ordinary `/v1/events` reads now return the newest bounded tail, while cursor-based `?since=` consumers retain ordered replay semantics.
- LOOK 4.42.0; Unified Node 5.0.0; Future Crash 1.1.14; Signal Window 1.0.0.

## 4.9.1 — Fast Edge

- Fixes the 4.9.0 installed-runtime packaging regression by installing and verifying `core/conductor.py` beside `fabric_client.py`.
- Adds an installed-layout smoke import so a coherent source tree can no longer pass release validation while the installed Fabric runtime is incomplete.
- Current weather with an explicit location now takes a deterministic WEATHER preflight edge before inference, eliminating the wasteful "ask model to call obvious tool" round.
- Pure weather turns omit the full tool schema after a successful receipt, reducing prompt cost and allowing a text-only reflex model to phrase the result.
- Fabric telemetry now announces worker/model placement before inference and reports prompt-evaluation time separately from output evaluation.

## 4.9.0 — Reflex Conductor

- Added a zero-I/O deterministic conductor that classifies turns as reflex, balanced, or deep before placement.
- Fabric routing now combines hard capability filtering with residency, live load, measured qualification TTFT/tok-s, locality, model size, and work class.
- LO emits truthful `conductor` events and keeps the chosen worker/model sticky for the rest of the turn.
- Reflex work favors small warm models; deep/code/vision work favors capable larger models without adding an extra LLM round-trip.

# 4.8.0 — Fabric Dashboard

- Adds `lk dash`, a terminal-native Fabric operational cockpit built entirely over the existing node APIs.
- Shows nodes, model residency, live work, trust basis, HTTP pressure, services, recent events, and actionable warnings.
- Keeps mutation explicit: service restarts require confirmation; watch/settings/doctor remain separate tools reached from the dashboard.
- Preserves 4.7.4 socket ownership and control-plane hardening.
- LOOK 4.40.0; Unified Node 4.8.0; Signal Window remains 1.0.0.

# 4.7.4 — Fabric Socket Ownership

- Fixes the 3090 control-plane failure captured with a full 7332 listen backlog and unaccepted CLOSE-WAIT sockets.
- Makes local HTTP socket ownership explicit: every accepted socket has one handler and one guaranteed shutdown path.
- Detects repeated accept() failures instead of hot-spinning with a full kernel backlog; dumps thread state and exits for systemd/launchd recovery.
- Explicitly closes every SQLite Fabric connection instead of relying on interpreter finalization.
- Extends HTTP telemetry with accept-error evidence.
- Adds abrupt-disconnect/control-plane stress regression coverage.
- LOOK 4.39.4; Unified Node 4.7.4; Signal Window remains 1.0.0.

# 4.7.3 — Fabric Ingress Guard

- Moves Tailscale-facing :7333 ingress into a separate `fcl-ingress` process. The 4.7.2 split used two sockets in one Python process, so a process-wide stall could still strand both accept queues.
- Bounds remote ingress concurrency before requests reach the localhost node and gives incomplete request headers a short timeout.
- Adds accept-loop watchdogs that dump Python thread stacks and exit nonzero when the local node or ingress accept loop stops advancing, allowing systemd/launchd to recover with evidence.
- Adds `SIGUSR1` thread-stack diagnostics to the node and ingress processes.
- Wires `lk fabric http` to the existing Fabric HTTP telemetry command.
- Unified Node 4.7.3; LOOK 4.39.3; Signal Window remains 1.0.0.

# 4.7.2 — Fabric Control-Plane Isolation

- Splits the node into two localhost listeners: local apps stay on `127.0.0.1:7332`, while Tailscale Serve proxies public `:7332` into isolated backend `127.0.0.1:7333`. Remote proxy pressure can no longer consume the local LO/Signal accept queue.
- Bounds HTTP concurrency independently on the two planes (64 local / 32 ingress) and rejects excess ingress work instead of spawning unbounded request threads.
- Adds `fcl-node http` / `/v1/http` pressure telemetry: accepted, active, completed, rejected, errors, endpoints, sources, and oldest active requests.
- Reconciles the Tailscale Serve backend on every top-level install, replacing the old `:7332 → :7332` route with `:7332 → :7333`.
- Reduces Fabric route selection to one `/v1/nodes` snapshot per placement attempt; removes duplicate and speculative routing polls.
- Restores host-rendered provenance receipts for WEATHER/WIKI/DATA/PLACE/PAPERS/ARCHIVE and web search; Signal surfaces the same structured source receipt from native LO events.
- LOOK 4.39.2; Unified Node 4.7.2; Signal Window remains 1.0.0.

# 4.7.1 — Trust Basis

- Injects an authoritative host-clock receipt into every LO turn; current date/time/offset come from the machine, never model memory.
- Treats current and forecast weather as a host-enforced fresh-data boundary. A prose-only weather answer is rejected and repaired into a WEATHER tool call.
- If a model still fails to obtain a live WEATHER receipt after repair, LO refuses to present fabricated current weather.
- Keeps temporal grounding local to the request so Fabric-routed inference receives the originating turn's trusted temporal frame.
- LOOK 4.39.1; Unified Node 4.7.1; Signal Window remains 1.0.0.

# 4.7.0 — Signal Native LO

- Replaces Signal's subprocess `lo --events-json` bridge with a reusable in-process LO engine. Human terminal output is no longer a machine protocol.
- Adds `look/lo_engine.py`, a structured machine edge around the mature LO tool/inference loop. Signal consumes response/tool/inference events directly.
- Adds bounded browser-session conversation history, so follow-ups such as “and in Los Angeles?” carry the prior turn without reconstructing a terminal session.
- `/clear` now clears both the Signal canvas/log and the server-side ephemeral LO session.
- Signal service recovers the configured Ollama web-search key without sourcing arbitrary shell startup code, giving the browser the same web capability when configured.
- Adds Signal-specific interface truth: LO must not invent lock state, latency, noise floor, or other fake Signal telemetry.
- Preserves Fabric-native inference, shared LO tools, browser artifact presentation, and opportunistic parallel Signal expression.
- LOOK 4.39.0; Unified Node 4.7.0; Signal Window 1.0.0.

# 4.6.7 — Fabric Control-Plane Pressure Fix

- Stops treating the one-second Fabric pulse as a reason to poll peers. Peer advertisements now refresh on a slow cadence with per-peer jitter and exponential backoff.
- Caches the complete local routing advertisement in memory. `/v1/advertisement` and `/v1/nodes` now serve snapshots rather than probing services or rebuilding routing state on demand.
- Adds explicit `Connection: close` to tiny control-plane HTTP requests/responses so abandoned proxy connections do not accumulate behind Tailscale Serve.
- Hardens the node HTTP listener with a 128-connection backlog and daemon request threads as defense in depth against transient proxy bursts.
- Throttles remote event polling in `lk fabric watch` while keeping the local display refresh responsive.
- Preserves deep `/health` diagnostics separately from cheap routing state.

# 4.6.6 — Fabric Control-Plane Hotfix

- Keeps `/v1/nodes` off slow Tailscale subprocess and SQLite health-check paths.
- Caches node identity in the pulse thread; request handlers read the last complete snapshot.
- Routing advertisements use worker heartbeat state; `/health` remains the deep SQLite diagnostic.
- Fixes Signal/LO failures that reported `0 worker attempt(s)` after repeated route-discovery timeouts.

# Future Crash + LOOK 4.6.6 — Fabric Routing Hotfix

- Fix Signal/LO self-contention: Signal no longer holds an exclusive node lease around Fabric-native LO work.
- Signal visual expression is opportunistic background work, so text conversation has priority and may preempt it.
- Fix non-streaming Fabric placement: selected remote `model.infer` jobs are now submitted to the selected worker rather than executed accidentally on the origin node.
- Streaming LO inference retries a pre-stream HTTP 409 / transport failure on another eligible Fabric worker and updates the sticky turn route.
- Preserve worker/model stickiness during healthy tool continuations; failover is exceptional rather than normal routing.
- LOOK 4.38.5; Unified Node 4.6.6; Signal Window 0.9.0.

### Routing hot-path fix
- `/v1/nodes` no longer waits behind Ollama model discovery; advertisements use the last complete model snapshot while the pulse thread refreshes models in the background.
- Fabric route discovery now retries transient control-plane timeouts instead of leaking raw `<urlopen error timed out>` failures into LO/Signal.
- This specifically targets intermittent Signal-spawned LO failures that appeared after the 15-second model cache expired.

