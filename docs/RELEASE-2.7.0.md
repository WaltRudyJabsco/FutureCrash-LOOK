# Future Crash + LOOK 2.7.0 — Services

Versions:

- Future Crash + LOOK: 2.7.0
- LOOK: 4.7.0
- Future Crash: 1.1.10

## Mental model

A LOOK machine can host several independent localhost services:

```text
Ollama        127.0.0.1:11434
ComfyUI       127.0.0.1:8188
Mercury       configured/discovered port
Web terminal  configured port
```

LOOK exposes them to the private tailnet with separate Tailscale Serve HTTPS listeners.

## Commands

```text
lk services
lk services discover
lk services set mercury PORT
lk services share all
lk services share comfy
lk services unshare all

lk share
lk share status
lk share off
```

Bare `lk share` means: share every configured service that is actually running on this computer.

## Stable endpoints

LOOK deliberately avoids making all services compete for the default Serve endpoint:

```text
Ollama    HTTPS :11435 → LOOK localhost proxy → Ollama :11434
ComfyUI   HTTPS :8188  → ComfyUI :8188
Mercury   HTTPS :PORT  → Mercury :PORT
```

This fixes the class of failure where exposing Comfy could replace the existing Ollama Serve route.

## Mercury Writer

LOOK attempts conservative Mercury discovery from running process command lines/listening ports. It never guesses a port.

If automatic discovery cannot resolve it:

```text
lk services set mercury 8765
lk services share mercury
```

Use Mercury's actual server port.

## Privacy

This uses Tailscale Serve, which is limited to devices/users permitted by the tailnet. LOOK does not automatically use Tailscale Funnel/public internet exposure.
