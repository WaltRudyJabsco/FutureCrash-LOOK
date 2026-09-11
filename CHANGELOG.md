# Future Crash + LOOK changelog

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
