# Future Crash + LOOK 6.1.8 — Media Player Edge Diagnostics

A queue that advances through every track at `0:00` proves that LOOK reached mpv but mpv rejected each source immediately. 6.1.8 moves the next diagnostic boundary to that player edge.

Local media is now written to the mpv playlist as its native filesystem path instead of a `file://` URI. The owned mpv process keeps a small persistent log instead of sending stderr to `/dev/null`. `lk media doctor` prints the resolved current source, local byte size when applicable, mpv version, a 250 ms null-output decode probe, and the tail of the player log.

This makes codec/container, filesystem, URL/proxy, and mpv-install failures distinguishable without changing the canonical MediaSession or Fabric media model.
