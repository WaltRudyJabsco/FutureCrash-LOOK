# 1.6.2 — Raster Signal Field

Versions:
- Future Crash + LOOK 1.6.2
- LOOK 3.8.0
- Future Crash 1.1.2

Signal now exposes the mental model that was already latent in the renderer: a 40×12 addressable character framebuffer. The model can choose among semantic, vector, and raster representations instead of treating Signal as only a tiny vector API.

## New primitives

```text
BARS x baseline_y color 0.15 0.32 0.75 0.91

SPRITE x y color
  .----.
 / o  o \
|   --   |
 \______/
END
```

`BARS` accepts normalized 0..1 values and leaves deterministic rasterization to Python. `SPRITE` preserves leading/trailing whitespace and treats spaces as transparent cells, allowing compact ASCII/pixel art to layer over other primitives. Both work inside normal Signal blocks and animation `FRAME`s.

Signal receipts now include semantic/vector/raster mode usage, nonempty-cell count, and occupied dimensions in addition to clipping, bounds, title, accepted/rejected command counts, and frame count.
