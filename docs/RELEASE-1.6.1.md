# 1.6.1 — Signal wiring fix

Versions:
- Future Crash + LOOK 1.6.1
- LOOK 3.8.0
- Future Crash 1.1.1

- Preserves valid `[[SIGNAL]]` blocks from structured model thinking while still hiding reasoning prose.
- Ask, Workstation, ambient, and scheduled Thread output can all reach the Signal parser.
- Restores a larger roughly 50/50 text/Signal layout in Oracle and Workstation views on desktop-width terminals.
- Removes the old 16-row cap from the desktop Signal pane.
- Built-in Dream requires a Signal render every wake.
- If a Dream wake returns no drawing, Future Crash renders a small host-side fallback dream instead of silently doing nothing.
- Ambient output rejects leaked Signal-language instructions as visible observation text.
