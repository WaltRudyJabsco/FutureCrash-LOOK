# Future Crash + LOOK 5.2.18 — LO Media Tools + LOOK Media Filter

This release closes two interaction gaps exposed by the media/Fabric demo without expanding LOOK into a media application.

## LO media capability

LO now has purpose-built Fabric media tools for catalog search, playback, queueing, and session control. Narrow local commands such as `lo play Talking Heads`, `lo pause`, `lo next track`, and `lo what's playing` are recognized as deterministic capability requests before general inference. Explicitly online requests are not intercepted.

The media tools resolve against the trusted Fabric-wide catalog. Exact artist, album, and title matches are stable groups; ambiguous fuzzy matches fail closed instead of playing an arbitrary set or silently escalating to the web.

## LOOK-native media selection

`lk media find` and `lk media browse` now use the established LOOK interaction model:

- type to filter immediately
- arrows/J/K to move
- Tab to select/unselect multiple rows
- Enter or `P` to play the selected set (or focused row)
- `Q` to queue the selected set
- `A` to queue all visible matches
- `I` for compact item information
- `S` to save the selected set as a playlist
- `C` to clear selection
- Esc clears the filter first, then exits

Human-readable labels remain presentation. All actions retain the underlying catalog row, node location, and SHA identity where available.
