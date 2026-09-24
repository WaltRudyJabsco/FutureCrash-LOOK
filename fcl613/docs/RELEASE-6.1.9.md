# Future Crash + LOOK 6.1.9 — Media Root Repair

The 0:00 queue race was traced to a stale local catalog root. LOOK now treats a local catalog row whose path is missing as stale local state instead of silently converting it into a loopback Fabric stream. Remote catalog rows still use `/v1/media/item` normally.

Use `lk media scan --relocate OLD_ROOT NEW_ROOT` when a media disk has moved mount points. The command explicitly removes rows belonging to the old root and rescans the new root so stale duplicates are not retained.

mpv IPC request IDs are now integers, matching mpv 0.41's current contract.
