# 3090 Home Server Controller v0.5.0

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
