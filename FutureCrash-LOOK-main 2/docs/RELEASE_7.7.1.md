# Future Crash + LOOK 7.7.1 — FILTER MINUS

Interactive LOOK filtering now supports subtractive terms. Prefix a token with `\` to exclude matching names while preserving the existing whitespace-AND substring grammar. `\.` is intentionally special: it excludes dot-prefixed names without excluding ordinary filenames that contain extension dots. Negative-only and multiple-negative filters are supported.

`lk match` remains the separate deterministic glob/ranking tool (`v`, `t`, `n`, `--all`).
