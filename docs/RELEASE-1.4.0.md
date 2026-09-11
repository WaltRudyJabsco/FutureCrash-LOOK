# 1.4.0 — LOOK smart make

Versions:
- Future Crash + LOOK 1.4.0
- LOOK 3.7.0
- Future Crash 1.0.0

## Smart make
- `lmk FILE.ext` creates an empty journaled file.
- `lmk DIR/` creates a journaled directory and enters it.
- `lmk -f NAME` / `lmk -d NAME` provide explicit file/directory intent.
- Extensionless names prompt for directory vs file.
- Missing parent paths for file creation require confirmation.
- `mkd DIR` now delegates to `lmk -d DIR`.

## Undo
- New file creation is undoable only while the file remains empty and unchanged.
- Directory undo refuses once the directory is non-empty.
- Parent directories created as part of a LOOK make action are cleaned up when still empty.

## Completion
- Adds `_lmk` Zsh completion for explicit mode flags and parent-directory navigation.

Documentation/help/man/README have been synchronized.
