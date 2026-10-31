# 8.24.0 — Inline Wiki images and reading panes

Bundle/node/Albert integration **8.24.0**; LOOK **4.71.0**.

Wiki pictures appear at their positions between article paragraphs. Visible
blocks load asynchronously into fixed-height spaces, keeping the text steady.
ASCII is always available; Kitty clips native images at the viewport edges,
while iTerm uses sliced ASCII for partially visible pictures. `I` hides/shows
inline pictures, `M` toggles auto-image/ASCII, and `i` keeps the image gallery.
Saved no-pictures archives remain text-only; live requests are explicit.

`W` opens a shell pane from Wiki shelves, articles, link selectors and galleries,
and Books shelves/read-aloud. Books now displays the complete pane status.
Option/Alt-Shift-W focuses another pane; Ctrl-Shift-W closes the focused pane
with the existing Look Kitty profile. tmux retains its normal focus/close keys.
Bookokrat's own reader keys are unchanged.

Source anchors survive hint reflow and resizing with image blocks present.
Idle articles avoid needless repainting, native painting stays out of headers
and footers, and exiting closes image workers and their notification pipes.

Validation: affected regression suite **467 passed**. A real live Architecture
article retained matching plain/rich text across 855 paragraphs and placed all
12 pictures inline; its actual thumbnail and ASCII rendering were verified.
Generated references, shell syntax, installer dry-run and diff checks passed.
