# Future Crash + LOOK changelog

## 1.5.1 — Future Crash final-only output

- Fixes reasoning leakage into fortunes and ambient/oracle observations.
- Adds a dedicated Future Crash personality file, independent of LO personality selection.


## 1.5.0 — personality + live thinking

- Adds four selectable/versionable LO personality packs.
- Adds thinking depth and compact/full/quiet live thinking display.
- Adds rolling Ollama streaming UX.
- Polishes `lmk` existing-path reporting.


## 1.4.2 — lmk directory-entry fix

- Removes output parsing from `lmk -d` and prompted directory creation.
- Directory entry now follows successful creation and an actual filesystem existence check.


## 1.4.1 — prompt input fix

- Fixes doubled characters in LOOK action prompts.
- `lmk` directory/file decisions now use immediate single-key choices.


## 1.4.0 — LOOK smart make

- `lmk` becomes a unified, journaled file/directory creation command.
- Adds safe undo for new files, directory-and-enter behavior, ambiguity prompts, and completion.


## 1.3.4 — media status feedback

- Media transport reports resulting player state/track after every successful action.
- macOS status uses direct state/artist/title queries.


## 1.3.2 — macOS media detection fix

- Uses direct AppleScript app-running checks for Music and Spotify.


## 1.3.1 — fast media aliases + paged intelligence views

- Adds `mm`, `mn`, and `mp` for play/pause, next, and previous.
- Routes `lk memory` and `lk skills` through LOOK's pager.


## 1.3.0 — media transport + versioned intelligence

- Adds `lk media` status/play-pause/next/previous/stop.
- Separates application versions from memory schema and skills-pack versions.
- Bundled skills can update without overwriting locally Learned craft.
- Rewrites the GitHub README around installation, first use, architecture, AI, memory, skills, and reference material.


## 1.2.1 — durable memory lifecycle

- Explicit long-term memory requests promote immediately into the semantic summary.
- LO no longer claims memory is session-only when persistence is asynchronous.
- Candidate duplication is consolidated.
- Long-term memory periodically rewrites itself under a hard 180-word cap and may forget stale or superseded facts.


## 1.2.0 — version safety + command grammar

### Version baseline
- Future Crash + LOOK 1.2.0
- LOOK 3.5.0
- Future Crash 1.0.0

### Installer
- Writes product/component versions to `~/.local/share/look/install_manifest.json`.
- Same-version installs reconcile owned files.
- Version-aware downgrades are refused unless `--force-downgrade` is supplied.
- Installer ownership metadata is preserved across upgrades.
- Fixes the optional Terminal Experience prompt to use the existing installer prompt helper.

### Completion
- Adds context-sensitive Zsh completion for `lk`.
- Adds LO option/host completion without trying to complete natural-language prompts.
- Saved Ollama hosts are read dynamically for completion.
