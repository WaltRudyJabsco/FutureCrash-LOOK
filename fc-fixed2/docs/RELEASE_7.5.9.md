# 7.5.9 — SIDE FRAME

- Restores the wide-terminal LOOK preview to its original left-list / right-preview geometry.
- Native Kitty/iTerm/Sixel previews are cursor-positioned into the same right-hand pane instead of being moved below the list.
- Chafa receives the exact right-pane viewport and bottom/center alignment, keeping graphics below the LOOK header and inside the terminal frame.
- Interactive cursor movement no longer issues a full-screen `ESC[2J` clear on every selection; LOOK homes the cursor, overwrites the frame, and erases only the stale tail.
- Preserves 7.5.8 deterministic filter selection: query changes select the first visible match; arrows move the visible selection; Enter opens that selection.
