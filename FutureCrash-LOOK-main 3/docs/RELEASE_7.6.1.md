# 7.6.1 — SETTLED PORTAL

- Native previews are deferred behind a 75 ms input-idle gate. Rapid navigation never renders obsolete selections.
- Correct Kitty delete command includes the required empty payload delimiter and suppresses error replies.
- Native preview height is capped at 32 terminal rows to bound payload size.
- Ctrl-C during a native write exits LOOK cleanly rather than producing a traceback.
- The left-list/right-preview geometry, filter selection contract, PDF raster preview, and 7.6.0 portal placement remain intact.
