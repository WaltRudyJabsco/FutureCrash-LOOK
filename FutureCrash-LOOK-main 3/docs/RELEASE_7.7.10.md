# 7.7.10 — REMOTE PLAYBACK

Built directly from 7.7.9 MEDIA IDENTITY. This release fixes the remaining remote Fabric media identity failure without changing local mpv playback, Media Session ownership, transport shortcuts, preview rendering, or audio-device routing.

The source node now backfills deterministic ids when publishing legacy media rows that predate persisted ids, and the byte-serving resolver derives the same identity independently. A path hint remains a bounded compatibility repair and is accepted only when it resolves to a row already present in that node's media catalog.
