# 1.3.0 — Media transport + versioned intelligence

Versions:
- Future Crash + LOOK 1.3.0
- LOOK 3.6.0
- Future Crash 1.0.0
- Memory schema 1
- Skills schema 1
- Bundled skills pack 1

## Media
- Adds `lk media [status|toggle|next|prev|stop]`.
- macOS adapter supports running Music and Spotify.
- Linux adapter uses MPRIS through `playerctl`.
- Adds Zsh completion and documentation for media actions.

## Intelligence versioning
- Memory JSON now carries `schema_version`.
- Skills Markdown now carries `schema` and `bundled-version` metadata.
- `lk skills version` reports the installed craft layer.
- `lk skills update [FILE]` replaces compatible Bundled craft while preserving Learned craft.
- Existing pre-versioned skills files are upgraded without losing their Learned section.

## README
- Rewritten as a new-user guide instead of accumulated release archaeology.
- Restores explicit `chmod +x install.sh` explanation.
- Preserves the screenshot paths supplied for the GitHub repository.
