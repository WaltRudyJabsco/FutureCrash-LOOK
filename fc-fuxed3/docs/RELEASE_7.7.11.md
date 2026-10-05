# 7.7.11 — FABRIC AUDIO RESTORE

Built from 7.7.10 with the media transport contract restored from the known-working Fabric/Signal implementation.

- Catalog objects: `/v1/media/item?node=...&id=...`
- Active queue stream: `/v1/media/audio?node=...&index=...`
- Signal `/api/media/audio` remains a browser-facing facade and translates item IDs to `/v1/media/item`.
- LOOK remote catalog playback uses the same `/v1/media/item` edge.
- Range-capable ingress, Media Session controls, local mpv behavior, JPEG/native previews, and installer fixes remain unchanged.
