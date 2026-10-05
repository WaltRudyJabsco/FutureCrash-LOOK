# 5.4.1 — Playback Ownership + Controller Repair

Fixes a media ownership regression in 5.4.0 where LOOK removed the mpv IPC pathname before probing the existing worker. Repeated play requests could therefore orphan a still-playing mpv process and launch another. LOOK now probes/reuses first, reaps only mpv processes carrying its exact IPC marker when the socket is stale, and `stop`/queue clear terminate all LOOK-owned playback workers without touching unrelated mpv sessions.

Explicit next-album phrases take the deterministic media fast path. The optional Local Labs `server` controller upgrade now normalizes the canonical installation/symlink while updating the legacy 3090-server copy when present, so `server status openjev` is available after upgrade.
