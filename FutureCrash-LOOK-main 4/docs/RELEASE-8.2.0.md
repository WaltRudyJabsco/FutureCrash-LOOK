# 8.2.0 — FABRIC EVERYWHERE

- Harden LOOK preview: bounded 64 KiB reads; special files never opened as preview streams.
- Clean Ctrl-C through renderer and `lk` wrapper.
- Add zero-touch removable-media watcher on macOS/Linux; new mounted drives join the local
  media catalog without copying media bytes and without duplicating explicitly indexed roots.
- Install the watcher as a boot/login service beside the node and ingress services.
- Enlarge Tic-Tac-Toe, Chess, and Checkers terminal boards while preserving their game logic.
- Preserve Global Thermonuclear War mechanics/timing unchanged.
- Media transport, Signal, Albert queue playback, `/v1/media/item`, and mpv session paths unchanged.
