# Future Crash + LOOK 1.6.3

Surgical stability release.

## Fixed

Signal fallback dreams no longer crash when emitting a receipt. The 1.6.2 raster receipt work added a `modes` field to Signal statistics, but the fallback dream path still initialized the older stats shape. Signal stats now use one shared initializer for parser and fallback paths.
