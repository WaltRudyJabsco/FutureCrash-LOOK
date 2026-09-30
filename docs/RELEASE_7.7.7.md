# 7.7.7 — CLEAN HANDOFF

- Linux `playerctl` is optional and distribution-owned; its absence or install failure can never abort LOOK/Fabric installation.
- Repair mpv liveness: IPC reachability is distinct from `idle-active`; a loaded playing/paused item is the only LOOK transport owner.
- MM/MN/MP no longer resurrect or mutate a stopped LOOK queue. A currently playing Music/Spotify/MPRIS player wins transport; an explicitly paused remembered system owner may retain it.
- Explicit `lk media play` may still intentionally resume the saved LOOK queue.
- Linux JPEG native preparation uses ImageMagick 7 correctly (`magick input ...`), while legacy `convert` remains supported.
- `lk media doctor` now probes the source URL directly and reports HTTP status/range evidence before invoking mpv.
- Carries forward the 7.7.6 streaming ingress fix; once every participating node is upgraded, remote `/v1/media/item` responses stream rather than buffer behind the control timeout.
