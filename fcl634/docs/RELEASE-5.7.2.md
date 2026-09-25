# Future Crash + LOOK 5.7.2 — Find Retrieval Repair

This release repairs the first Fabric Content Search retrieval bug and turns `lk find` into an interactive LOOK workflow.

- Unified Node now tokenizes file queries correctly.
- Lexical misses return zero results instead of the newest catalog rows.
- Explicit metadata queries such as `recent files` continue to work.
- Interactive `lk find` is paged, filterable, and selectable.
- Accepting a local result enters the ordinary LOOK file view with that path selected, preserving the existing action surface.
- Remote Fabric results are not silently executed against the local filesystem.

No catalog rebuild is required. Existing FTS5 content indexes remain valid.
