# 7.2.0 — CAPABILITY CURATOR

7.2.0 adds automatic host-capability curation beside model curation.

## Mental model

`JEV → typed referent → curated capability → host adapter → receipt`

Discovery is non-destructive and automatic. A node records which adapters are
present, advertises their typed actions through Fabric, and promotes an adapter
from `discovered` to `proven` only after successful ordinary use. Permission
remains separate: capability evidence never bypasses LO's access profile.

## First curated object family

`terminal_window` now supports close, focus, maximize, minimize, and fullscreen
when the host advertises an adapter. macOS uses Terminal window IDs and
AppleScript. Linux assigns every launched terminal a stable LOOK token and a
private control FIFO; `wmctrl`/`xdotool` are preferred when present, while the
zero-dependency terminal control channel remains a bounded fallback.

`lk capabilities` is an observability/debugging surface. Users normally do not
need to configure or refresh the catalog themselves.
