# Future Crash + LOOK 8.9.0 — FABRIC MEDIA

8.9.0 stabilizes the Phase-2 refactor and makes cross-node media a first-class Fabric path rather than a collection of local special cases.

## Highlights

- Fabric media catalog enrichment is concurrent and bounded instead of serial and stall-prone.
- Remote playback follows physical media ownership correctly across Fabric nodes.
- Sleeping and removable media get bounded wake-up behavior instead of being prematurely discarded.
- Signal browser playback now requests media from the queue item's byte-owning node rather than confusing media ownership with output-session ownership.
- Remote terminal previews and player artwork work across Fabric nodes.
- Classical, classics, and arts routing is restored.
- LOOK narrow previews and selection-following behavior are repaired.
- Older-Python f-string compatibility regressions were removed.
- LOOK FILTER reserves printable letters for search text: lowercase q no longer quits.
- Uppercase Q is the explicit LOOK quit key.
- Destination filtering no longer steals q, j, or k from alpha-search.
- Media pinning treats bounded remote timeout as optimistic reachability rather than false absence.

## Verification

Release verification includes structural health, Python syntax, shell syntax, JavaScript syntax, and the full regression suite.

