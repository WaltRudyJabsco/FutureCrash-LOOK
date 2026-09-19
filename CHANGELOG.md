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

