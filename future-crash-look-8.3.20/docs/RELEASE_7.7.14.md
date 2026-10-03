# 7.7.14 — BROWSER MEDIA

Repair Signal and Albert browser playback without changing native LOOK/mpv playback.

- Signal browser playback now prefers a catalog item ID over an incidental SHA-256 checksum. A checksum no longer promotes an ordinary song into artifact transport.
- Signal issues a short-lived, resource-scoped media ticket before attaching an audio/video URL. Safari's media process can therefore make Range requests without depending on propagation of the browser's HttpOnly endpoint cookie.
- Albert emits the same kind of short-lived ticket for prepared Fabric media items.
- Tickets are bound to one exact node/item (or artifact) and expire after ten minutes; they do not make media endpoints public.
- Existing Fabric `/v1/media/item`, LOOK/mpv, MM/MN/MP, All Classical, and Classic Arts paths are frozen by regression tests.
