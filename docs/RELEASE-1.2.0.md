# 1.2.0 — Version safety + command grammar

Version baseline:
- Future Crash + LOOK 1.2.0
- LOOK 3.5.0
- Future Crash 1.0.0

## Version-aware installation
- Writes canonical product/component versions to `~/.local/share/look/install_manifest.json`.
- Preserves installer-owned package/directory metadata across updates.
- Refuses a downgrade from a version-aware installer by default.
- Adds `--force-downgrade` for deliberate rollback.
- Same-version installs reconcile owned files.
- Historical installers predating the guard cannot be retroactively protected.

## Zsh completion
- Adds context-sensitive `_lk` and `_lo` completion definitions.
- Completes LOOK/Ollama/memory/skills grammar.
- Dynamically completes saved Ollama hosts.
- LO completion intentionally stops where natural-language prompting begins.

Also fixes the Terminal Experience prompt to use the installer's existing `ask` helper.
