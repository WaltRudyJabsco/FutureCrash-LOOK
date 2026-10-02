# 8.2.1 — INSTRUMENT PANEL

A field-driven polish release: make removable media observable, make Media Find diagnostic, make the games visibly larger, restore the WOPR doorway, and extend the existing Dash rather than replacing it.

## Media
- Removable-media watcher publishes `watching`, `scanning`, `indexed`, and `error` state in `~/.local/share/look/media_watch.json`.
- `lk media library` shows current removable-volume state and item count.
- Media Find `I` opens a persistent provenance panel with node, media ID, format, bytes, root, full path, identity, and availability.

## Games
- Chess and Checkers use wider cells and double-height ranks for a materially larger CRT board.
- Successful `JOSHUA` login from bare `lk games` now enters the actual simulation launcher instead of the broken `NO GAMES INSTALLED` dead end.
- Game engines and Global Thermonuclear War dispatch/timing are unchanged.

## Dash
- Existing responsive Dash, Mini mode, controls, and Fabric presentation remain intact.
- Adds compact local media/root/removable status.
- Adds a tiny deterministic Signal heartbeat driven by recent activity; no model invocation and no background allocation-heavy renderer.
- Full-layout recent activity is denser to make room without inflating the dashboard.

## Verification
- 589 tests.
- Python compileall clean.
- Both installers pass shell syntax checks.
