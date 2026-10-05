# Fabric Vision 1.0

Fabric Vision gives a trusted Future Crash + LOOK node the ability to answer one question: **what is on this endpoint's screen right now?**

It is deliberately pull-only. The Unified Node does not run a screenshot timer, maintain a frame ring, or write a screenshot history. Each `/v1/vision/screen` request creates one temporary capture, optionally compresses it to bounded WebP, hashes it, returns it to the authenticated requester, and deletes the temporary files.

## Human interface

```text
lk vision screen
lk vision screen @m4
lk vision screen @m4 --ask "what is wrong with this UI?"
lk vision screen @m4 --save ~/Desktop/m4.webp
lk vision screen @m4 --watch 30s --every 5s
```

The ordinary one-shot command renders the frame with Chafa when available. `--ask` sends the received bytes directly to the selected local Ollama vision model. `--save` is the only normal screen-vision path that deliberately persists a received screenshot.

## Watch semantics

Watch belongs to the requesting CLI, never to the endpoint daemon. It is a foreground loop, stops on Ctrl-C or the requested duration, is capped at ten minutes, and polls no faster than every two seconds. Each request includes the previous frame hash. If the new capture hashes identically, the endpoint returns metadata only and omits image bytes.

This reduces network transfer without hiding the important distinction: the endpoint still takes a fresh screenshot on each explicit watch poll so it can determine whether the pixels changed.

## Trust and privacy

Remote `/v1/vision/screen` is protected by the same paired Fabric authentication as other remote node capabilities. Unpaired ingress cannot capture a screen. The response declares `ephemeral: true` and `stored: false`; these describe server behavior, not a promise about a caller that explicitly chooses to save the bytes.

macOS may require Screen Recording permission for the process running the Unified Node. Linux capture depends on the active desktop/compositor and one supported native tool (`grim`, `gnome-screenshot`, `spectacle`, `scrot`, or ImageMagick `import`). Headless nodes correctly report screen capture as unavailable.

## Transport contract

`GET /v1/vision/screen` accepts `node`, `previous_hash`, `max_width`, and `quality`. A successful changed frame returns SHA-256 hash, MIME type, byte count, provider metadata, and base64 image bytes. An unchanged frame returns the same metadata and hash with `changed: false`, omitting `image_base64`.

Frames are bounded to 6 MiB after compression. Default transport width is 1600 pixels and default WebP quality is 72. Fabric relays use authenticated peer headers and existing pinned TLS/Tailcat/Tailscale routing.
