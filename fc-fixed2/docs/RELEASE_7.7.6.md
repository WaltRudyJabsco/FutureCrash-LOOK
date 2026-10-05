# 7.7.8 — MEDIA SESSION

A narrow media-boundary repair on top of 7.7.5 TRUE FRAME.

- Fabric ingress now streams `/v1/media/item`, `/v1/media/artifact`, and artifact byte routes instead of buffering them as control responses. Range requests retain byte-length/range metadata for mpv and browser seeking.
- Linux JPEG native preview fixes the ImageMagick first-frame selector (`file.jpg[0]`), while PNG direct and PDF/Poppler paths remain unchanged.
- `mm`, `mn`, `mp` remain play/pause, next, previous, but transport is now routed to one active owner: live LOOK/mpv first; otherwise an actively playing or previously claimed paused system player; only then a saved LOOK queue.
- macOS Music/Spotify and Linux MPRIS are adapters to the same transport contract. Explicit play/pause no longer degrade to toggle. Linux installs `playerctl` with workstation dependencies.
- Media state exposes owner, source node, and playback node for Fabric-aware status surfaces.
