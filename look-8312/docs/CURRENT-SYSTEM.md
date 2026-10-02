# Future Crash + LOOK 8.0 — Current System

This document describes the current system. Release history describes how it got here.

## Ownership

- **LOOK / `lk`** — keyboard-first terminal surface, files, local tools, media session controls.
- **LO** — natural-language cognition and tool routing.
- **Fabric / Unified Node** — node identity, discovery, remote actions, shared media catalog, byte transport, artifacts and endpoint dispatch.
- **Signal Window** — expressive browser endpoint and proven browser-media surface.
- **Albert** — quiet browser work surface. Albert owns browser playback presentation; Fabric resolves media and transports bytes.

The core/edge rule is deliberate: Fabric identifies and transports an object; an endpoint decides how to present or play it.

## Network ports

- `127.0.0.1:7332` — Unified Node / Fabric.
- `127.0.0.1:7333` — guarded Fabric ingress used for tailnet exposure.
- `127.0.0.1:7331` — Signal Window.
- `127.0.0.1:7330` — Albert.

Tailnet configuration is an edge concern. Local services must continue to work if tailnet exposure is unavailable.

## Media model

Three objects are intentionally different:

1. **Catalog** — discoverable media identities across Fabric nodes.
2. **Queue** — ephemeral playback state belonging to an endpoint/session.
3. **Playlist** — a named, persistent saved queue.

A new `play` replaces the active queue for that surface. Explicit queue/add operations append. Stop does not destroy a queue. Clear explicitly destroys it. Finishing the final track leaves the queue available for previous/restart.

Browser catalog playback uses durable `{node,id}` identity in UI state. Immediately before playback the browser obtains a short-lived scoped ticket, then requests Albert/Signal's same-origin media facade. The facade proxies the Range request to Fabric `/v1/media/item`. Do not pre-mint stream URLs into durable UI state.

## Media commands

- `lk media find QUERY` — filter/select the online Fabric catalog.
- `lk media browse` — browse the online catalog.
- `lk media play TARGET` — replace queue and play.
- `lk media queue` — inspect queue.
- `lk media clear` — stop and empty queue.
- `lk media save NAME` / `lk media load NAME` — persist/restore playlists.
- `lk media next`, `prev`, `toggle`, `stop` — transport controls.
- `mm`, `mn`, `mp` — toggle, next, previous aliases.

Media Find uses LOOK filtering: ordinary words are required; a leading backslash excludes a word. Example: `clash \\live \\remix`. Tab toggles one selection, Shift-A selects/unselects all visible results, Enter/Shift-P plays the selection/current row, Shift-Q queues it, Shift-S saves it, and Shift-C clears the selection.

## Known-good invariants

The native Fabric item route, LOOK/mpv playback, Signal browser playback, transport aliases, All Classical and Classic Arts are independent known-good paths. UI work should not rewrite these paths without a failing reproduction that requires it.

## Diagnostics

Prefer boundary tests over guesses. For browser media, verify in order: queue identity → ticket `200` → media request → HTTP `200/206` → `Content-Type`/Range headers → bytes. `ERR_EMPTY_RESPONSE` means the server closed the request before writing HTTP headers and should be debugged server-side.

## LOOK live view (8.1)

Interactive LOOK pins the directory header above the scrolling file viewport. `Shift-F` cycles NAME, MODIFIED, SIZE, KIND, and ADDED sorting for the current LOOK session; the highlighted object is preserved across a reorder. A new LOOK process begins with its launch/default sort.

## 8.2 removable media and startup contract

Future Crash + LOOK is zero-touch after a normal reboot: the Unified Node, guarded ingress,
and removable-media watcher are configured as user services (`systemd --user` on Linux,
LaunchAgents on macOS). Tailscale remains its own system-managed service.

The removable-media watcher detects user-mounted volumes (`/Volumes` on macOS and the
usual per-user `/run/media` or `/media` roots on Linux). A newly attached volume receives
a fast metadata-only media scan. Files remain on that physical disk; Fabric publishes the
owning node plus catalog identity and streams bytes from that node on demand. If an explicit
media root already exists inside a volume, it wins and the whole volume is not rescanned,
which prevents duplicate catalog rows. Unplugging a volume makes its files temporarily
unavailable but does not pretend they moved to another node.

LOOK previews are bounded edge work: regular-file text sniffing reads at most 64 KiB,
special files are not opened for preview, and Ctrl-C exits cleanly without nested Python
tracebacks.
