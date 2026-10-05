# Future Crash + LOOK 8.8.0 — RESOLVE FIRST

8.8.0 moves common human requests through a deterministic resolve stage before execution.

## Media

- `play some Stones` becomes an audio artist selector, resolves unique shorthand to the canonical catalog artist, selects a small random set, then plays through the existing Fabric MediaSession.
- `play Catalina video` and `play video Catalina` keep `video` as a type constraint and search `Catalina` as the query.
- Ambiguous artist shorthand is not guessed.
- Signal feedback prefers canonical artist/title metadata from the resolved queue.

## Fabric Vision displays

- `lk vision displays [@NODE]` lists numbered displays.
- `lk vision screen --display 2`, `--displays 1,3`, and `--all` select explicit displays.
- Each display is captured and transported separately; no stitched mega-frame or background capture loop is introduced.
- Backends that cannot target one display fail explicitly instead of returning the wrong screen.

## Performance model

Obvious media language remains on the deterministic fast path. Model inference is reserved for requests whose meaning cannot be safely resolved from rules, aliases, and canonical Fabric state.
