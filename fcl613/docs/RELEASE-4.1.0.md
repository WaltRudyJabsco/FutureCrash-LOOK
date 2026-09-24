# 4.1.0 — Fabric Pulse

4.1 turns the Unified Node from a static endpoint into a small distributed supervisor.

## Fabric pulse

Every node derives a one-second `unix-1s-v1` pulse from ordinary synchronized wall time. Jobs, events, streams and cancellation remain immediate; nothing waits for the pulse. The pulse is a reconciliation backstop for freshness, stale leases, peer presence and background work.

## Jobs and leases

The supervisor now tracks priority, phase, progress age and health (`healthy`, `quiet`, `stale`). Interactive/follow-up work can preempt a background lease. The pulse never kills work merely because it is old: progress age is the important signal.

## Model advertisements

`/v1/advertisement` and `/v1/models` expose installed Ollama models, declared Ollama capabilities, residency, parameter/quantization metadata and node-local qualification evidence. No single synthetic quality score is invented. Vision/tools/thinking/embedding eligibility is kept separate from measured speed.

An idle node may run a tiny qualification only against an already-resident, not-recently-tested model. It never cold-loads models in the background. Qualification is a background lease and yields to interactive work. Results persist in `~/.local/share/future-crash-look/model_profiles.json`.

## Cross-node discovery

Peers discovered through Tailscale are probed for their node advertisement on HTTPS :7332. Advertisements have short-lived operational meaning; peers without a reachable node remain ordinary Tailscale peers rather than errors.

## Repairs from 4.0.0

- Signal's missing node helper functions are now implemented, so its request lifecycle really reaches `/v1/activity`.
- Node service PATH discovery now checks canonical user locations, fixing false LOOK/LO negatives.
- Canonical node identity prefers Tailscale's hostname when available.
- The installer restarts updated node/Signal services rather than merely enabling already-running units.
- The installer owns :7332 Tailscale publication when possible and prints one exact repair command when privilege is required.
- Signal installation now has Linux systemd and macOS launchd edges.

## Human interface

`fcl-node fabric`, `models`, `pulse`, `activity`, `nodes`, and `qualify MODEL` expose the machinery directly. LOOK adds `lk fabric` as the normal front door.
