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

