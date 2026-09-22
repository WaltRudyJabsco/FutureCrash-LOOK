# Local Labs Host Controller v0.5.1

A normal Linux control layer for the 3090 host. systemd, Tailscale and the underlying services remain authoritative.

## 0.5.0

- Adds **Signal Window** as a first-class discovered service on port 7331.
- Adds the **Operator Console** to service discovery on port 3090.
- `server status signal` now distinguishes local health from Tailscale publication, so a published-but-dead backend is obvious instead of merely surfacing as a browser 502.
- `server expose signal` / `server unexpose signal` work through the generic Tailscale Serve path.
- Fixes the exposure-state bug that checked the wrong `tailnet` key instead of `tailnet_url`.
- Doctor checks Signal when it is installed or published.
- Fixes the installer’s stale `SCRIPT_DIR` bug.
- Installer no longer edits `.zshrc`; the real `~/.local/bin/server` command is sufficient.
- Operator Console understands the current snapshot schema and can restart Signal.

## Install / upgrade

```bash
./install.sh
server version
server status
server doctor
```

Expected version: `0.5.0`.

## Signal Window

Install Signal Window separately so it owns its own app files and systemd unit. Once installed:

```bash
server status signal
server start signal
server expose signal
```

A healthy published Signal should show both a live local endpoint and a tailnet URL. If the route exists but the local backend is down, `server status` reports `route/down` and Doctor flags it.

## Safety boundary

The controller does not become a second supervisor. It observes and invokes systemd/Tailscale explicitly. The browser console does not expose arbitrary shell, reboot, or shutdown.


## 0.5.1 — host portability + Ollama share health

The controller now treats the machine as a **Local Labs Host**, not as permanently synonymous with one RTX 3090 Linux box. Discovery uses portable socket/HTTP checks where possible, macOS system/memory/disk discovery is supported, and Linux systemd lifecycle remains an OS-specific adapter rather than part of the service model. A future Apple Silicon host can therefore implement lifecycle with launchd without changing the public `server` vocabulary.

Ollama reporting now separates the three remote-inference layers: local API `11434`, LOOK host-rewrite proxy `11435`, and the Tailscale publication. A published `:11435` route with a dead localhost proxy is reported explicitly.

## Optional decision worker

When OpenJev is installed/adopted by Future Crash + LOOK, the Local Labs controller recognizes it as the optional `openjev`/`decision` service. Use `server status openjev`, `server start openjev`, `server stop openjev`, or `server restart openjev`. Machines without it continue normally.
