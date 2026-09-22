# 5.4.1 — Canonical Decision Worker

OpenJev graduates from an experimental shadow endpoint to an optional first-class Fabric worker. The architecture remains capability-first: the Decision Plane owns authority and policy; OpenJev contributes typed judgment evidence only.

## Cognitive path

Exact commands stay deterministic. Bounded ambiguous media language may be sent to OpenJev with current media state. The normalized result includes the selected candidate, distribution, confidence, top-two margin, latency, and a deterministic policy disposition (`act`, `ask`, `think_more`, or `abort`). Low-risk reversible work may proceed when evidence is strong; consequential or irreversible work never gains authority from a learned worker.

## Lifecycle

`./install.sh` defaults to `--openjev=auto`: adopt an existing compatible `~/.local/share/open-jev` installation if present, otherwise continue with the fallback path. `--openjev=install` is the only mode that may clone OpenJev and download its pinned 2B checkpoint. `--openjev=off` deliberately disables it; `--openjev=adopt` attempts adoption without downloading. Linux installs `future-crash-look-openjev.service` and the Local Labs controller can operate it with `server start|stop|restart openjev`.

## Observability

Decision judgment emits Fabric events containing provider, probabilities, confidence, margin, and latency. Dash renders JUDGE/ASK in amber, resolved human decisions in green, provider failures in red, and exposes a cognition/decision panel alongside normal Fabric state.

## Graceful degradation

OpenJev is never required to start LOOK, LO, Fabric, Signal, or the node. Connection failure trips a bounded backoff and the caller falls back instead of repeatedly paying a dead endpoint.
