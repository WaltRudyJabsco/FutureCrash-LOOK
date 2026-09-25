# Future Crash + LOOK 4.0 — Unified Node

4.0 makes the distribution honest: one install, one shared node, several interfaces.

## Invariants

- The UI never owns inference state.
- Slow work is observable and cancellable by design.
- Interactive work outranks follow-up work; follow-up outranks background work.
- Every machine runs the same node and advertises only capabilities it actually has.
- Tailscale is transport, Ollama is inference, Unix is the substrate; Local Labs does not reimplement them.
- Platform differences live at the service/install edge (systemd on Linux, launchd on macOS).

## 4.0 foundation

The node listens locally on 127.0.0.1:7332 and exposes `/health`, `/v1/node`, `/v1/capabilities`, `/v1/nodes`, `/v1/activity`, and lease acquire/progress/release endpoints. Signal 0.5.2 is carried forward visually unchanged but now participates in the shared activity lane. This first 4.0 build deliberately preserves LOOK/LO/Future Crash behavior while moving coordination underneath them.

The next reliability pass moves LO execution itself behind the supervisor, adds streaming events and real cancellation, then lets LOOK and Future Crash consume that same event stream.
