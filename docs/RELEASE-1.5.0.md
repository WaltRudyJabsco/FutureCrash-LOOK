# 1.5.0 — LO personality + live thinking

Versions:
- Future Crash + LOOK 1.5.0
- LOOK 3.8.0
- Future Crash 1.0.0

## Personality
Adds four inspectable Markdown personality packs: LO, Space Robot, Max, and Philosopher. Selection is persistent and independent of model/access/memory/skills.

## Thinking
Adds light/adaptive/deep reasoning guidance and compact/full/quiet thinking display modes. Compact uses Ollama streaming to show rolling readable thought chunks while work is happening.

## Settings
All personality and thinking controls are available in `lk settings` and as direct commands, with Zsh completion.

## Smart make polish
`lmk` now checks an existing target before asking file-vs-directory intent and reports whether the collision is a file or directory.
