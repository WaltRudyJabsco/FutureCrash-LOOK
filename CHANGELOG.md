# Future Crash + LOOK 4.6.3 — Fabric Contention Hotfix

- Fix Signal/LO self-contention: Signal no longer holds an exclusive node lease around Fabric-native LO work.
- Signal visual expression is opportunistic background work, so text conversation has priority and may preempt it.
- Fix non-streaming Fabric placement: selected remote `model.infer` jobs are now submitted to the selected worker rather than executed accidentally on the origin node.
- Streaming LO inference retries a pre-stream HTTP 409 / transport failure on another eligible Fabric worker and updates the sticky turn route.
- Preserve worker/model stickiness during healthy tool continuations; failover is exceptional rather than normal routing.
- LOOK 4.38.3; Unified Node 4.6.3; Signal Window 0.9.0.
