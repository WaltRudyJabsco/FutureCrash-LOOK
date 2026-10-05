# Future Crash + LOOK 5.6.2 — Deterministic Smart Resolver

LOOK now separates command grammar from human phrases. Exact paths remain exact. A single unresolved argument may be resolved through the local metadata catalog; quoted phrases such as `lk open "labs folder"` therefore gain interpretation without making unquoted multi-argument LK commands fuzzy.

The resolver infers directories from indexed file parents, chooses only deterministic strong matches, reports ambiguity instead of guessing, and refuses stale catalog entries. `open`, `preview`, and `reveal` share the same resolver.

This is intentionally lexical and local. LO remains the conversational layer; future LO intent handling can feed structured targets into the same resolver.
