# 7.6.2 — QUIET FRAME

A renderer/state correction cut from 7.6.1.

- Filter frames erase each rewritten terminal line to the right edge, preventing stale unfiltered directory columns from surviving behind the preview pane.
- Filter Up/Down moves the highlight through visible rows; the list scrolls only when the selection reaches a viewport edge.
- Native graphics are not deleted at frame start. The previous preview remains until a replacement payload is ready, then LOOK deletes/replaces it in one step.
- Native preview settle time is 180 ms so ordinary typing and arrow bursts do not trigger intermediate PNG/PDF renders.
- Existing right-side preview geometry, graphical PDF page-one previews, filter header, and 7.6.1 Kitty lifecycle fixes are preserved.
