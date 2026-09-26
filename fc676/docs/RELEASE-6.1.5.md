# Future Crash + LOOK 6.1.5 — Media Stream Edge Repair

6.1.5 repairs the final media-source edge exposed by 6.1.4. A playable queue no longer depends on parsing one `fcl-node artifact --json` subprocess result per track.

## Playback boundary

Local files are still used directly when available. Identified media whose path is not directly usable is represented to the player as a loopback URL under `/v1/media/artifact`. The Unified Node resolves the owning Fabric node, attaches authorization, applies pinned Tailcat TLS, retries alternate peer transports, forwards Range/HEAD semantics, and streams bytes without buffering the whole object.

This keeps the player edge intentionally boring: mpv and browser audio never receive Fabric credentials and never need to understand Fabric trust or transport.

## Diagnostics

CLI JSON consumers tolerate bounded non-JSON startup chatter and report the output tail if no valid JSON value can be recovered.
