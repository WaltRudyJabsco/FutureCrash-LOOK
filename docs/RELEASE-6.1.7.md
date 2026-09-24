# Future Crash + LOOK 6.1.7 — Media + Signal Repair

This release repairs the remaining ordinary playback detour and makes Signal less visually noisy.

## Media

A scanned catalog entry is already sufficient playback identity. LOOK now hands local files directly to mpv when possible; otherwise it gives the player a loopback `/v1/media/item?node=...&id=...` URL. The local Unified Node resolves the owner, supplies Fabric authorization and pinned TLS, retries Tailcat/Tailscale transports, preserves Range/HEAD semantics, and streams bytes. No nested Fabric CLI and no SHA promotion are required just to listen.

## Signal player

A populated stopped queue remains visible in the Signal media card. This makes `/player` useful even when playback failed or was stopped, and avoids the flash-then-disappear effect.

## Signal visuals

Routine media controls and short command confirmations no longer trigger decorative Signal art. The generic deterministic fallback now abstains rather than drawing the recurring abstract mountain/sun-like micro-signal. Weather/news/explicit visual requests retain meaningful Signal scenes.
