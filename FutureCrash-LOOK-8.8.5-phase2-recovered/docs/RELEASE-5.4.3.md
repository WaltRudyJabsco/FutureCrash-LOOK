# 5.4.3 — Signal Media Card

Signal 1.3.0 becomes a live renderer/controller for LOOK's canonical MediaSession. A session started from terminal LO, `lk media`, or Signal itself is rediscovered automatically in the browser; no browser-owned audio engine or duplicate queue exists.

The compact card shows artist, title, album, playback state, progress, queue position and transport controls. Queue expansion exposes exact rows, and clicking a row uses deterministic `lk media jump INDEX`. Dismiss hides only the renderer. Stop is explicit and remains a LOOK/mpv transport action.

New deterministic surfaces:

```text
lk media state       compact JSON MediaSession snapshot
lk media jump INDEX  exact one-based queue selection
```

The release updates Signal help, LOOK command references, command grammar, man page, completions/documentation surfaces, installer/version markers, and regression tests.
