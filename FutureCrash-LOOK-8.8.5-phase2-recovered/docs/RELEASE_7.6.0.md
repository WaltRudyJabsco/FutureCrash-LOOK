# 7.6.0 — PREVIEW PORTAL

A managed LOOK preview surface built from 7.5.9.

- Keeps the wide-terminal file list on the left and preview pane on the right.
- Standardizes interactive native graphics on the Kitty protocol, including inside modern iTerm2, so LOOK can explicitly delete the previous visible placement before drawing the next one.
- Chafa renders relative to one fixed right-pane origin and bottom-centers within that bounded viewport.
- PDF page 1 is rasterized with pdftoppm (or macOS Quick Look fallback) and rendered through the same native preview portal as images.
- Sixel falls back to composable symbol preview until LOOK has a reliable placement lifecycle for it.
- Preserves deterministic filtered selection from 7.5.8/7.5.9.
