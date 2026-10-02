# 7.7.15 — BROWSER EDGE

Two isolated browser/installer repairs; media core remains frozen.

- macOS installer now retries the live ingress metrics endpoint before declaring :7333 unhealthy. A newly launched guard that is already listening but not yet answering its first probe no longer triggers a false rollback.
- Albert now implements HEAD for its ticketed `/v1/media/item` browser proxy, matching Signal's browser media contract and preserving Range-capable GET playback.

No changes to LOOK/mpv playback, `/v1/media/item` serving, MM/MN/MP, Signal's working browser-media implementation, All Classical, or Classic Arts.
