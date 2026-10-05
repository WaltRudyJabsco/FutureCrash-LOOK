# Future Crash + LOOK 6.2.0 — Common Tongue

6.2.0 adds a shared deterministic intent-normalization edge for obvious Fabric commands.

- English selectors stop at the edge: `play any movie` becomes `media.play {kind: video, selection: random}` instead of a literal catalog search for “any movie”.
- Signal and terminal LO use the same normalizer, so common commands mean the same thing on every surface.
- Named requests remain boring and exact: `play Talking Heads` keeps `Talking Heads` as the catalog query.
- Structured media selection supports audio/video kind, artist, random/all selection, limits, and shuffle without teaching the media core English.
- Signal Window 1.10.0 returns the normalized intent in deterministic media responses for inspection/debugging.
- This release deliberately does not add automatic transcoding. Browser codec/container compatibility remains an endpoint capability/fallback problem rather than being mixed into intent parsing.

The architectural rule is simple: **English at the edge; validated intent in the core.**
