# Future Crash + LOOK 3.3.11

Boot-persistence hardening for shared Ollama inference.

- `lk ollama share` now installs the existing 11435 host-rewrite proxy into the host's native per-user service manager: systemd on Linux, launchd on macOS.
- The proxy remains one LOOK implementation; service managers only supervise it.
- The proxy writes its own PID so health reporting is identical whether launched directly or by a service manager.
- `lk ollama share status` reports proxy health and persistence state.
- `lk ollama share off` disables the native service as well as the Tailscale publication.
- The installer detects an already-configured `:11435` Tailscale share and reconciles persistence without assuming Linux.

The topology remains machine-agnostic: a Linux GPU workstation, a future Apple Silicon host, or another Unix machine can provide Ollama without changing the client contract.
