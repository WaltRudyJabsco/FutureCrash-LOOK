# 1.4.2 — lmk directory-entry fix

- `lmk -d NAME` no longer captures/parses LOOK's rendered mkdir output.
- Prompted directory creation uses the same direct path.
- Directory creation succeeds via `lk _mkdir`, then `lmk` enters the directory only after verifying it exists.
- Keeps the 1.4.1 single-key prompt fix.

Versions:
- Future Crash + LOOK 1.4.2
- LOOK 3.7.2
- Future Crash 1.0.0
