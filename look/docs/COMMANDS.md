# Future Crash + LOOK command reference

`lk help` is canonical. This compact repository reference is synchronized with the live glossary.

## LOOK
`lk [THING]` · `lk [PATH]` · `lk detail` · `lk dirs` · `lk files` · `lk tree` · `lk recent` · `lk size` · `lk run`

## Inspect
`lk up` · `lk ports` · `lk port NUMBER` · `lk process TERM` · `lk processes` · `lk pid NUMBER` · `lk git` · `lk machine` · `lk gpu` · `lk disk` · `lk net` · `lk tailscale` · `lk env` · `lk path` · `lk why COMMAND`

## LO / Ollama
`lo [ASK]` · `lo search [ASK]` · `lo @HOST [ASK]`
`lo --conservative` · `lo --workspace` · `lo --power` · `lo --unsafe`

`lk ollama`
`lk ollama models`
`lk ollama test [--all]`
`lk ollama host`
`lk ollama host NAME`
`lk ollama host local`
`lk ollama host NAME URL`
`lk ollama host forget NAME`
`lk ollama share`
`lk ollama share status`
`lk ollama share off`
`lk ollama key`
`lk ollama key status`
`lk ollama access [MODE]`

## Memory + craft
`lk memory` · `lk memory add TEXT [--importance N]` · `lk memory forget TEXT` · `lk memory clear` · `lk memory clear-summary` · `lk memory prune`

`lk forget TEXT` · `lk clear-memory`

`lk skills` · `lk skills add TEXT` · `lk skills forget TEXT` · `lk skills clear-learned` · `lk skills path` · `lk skills export [FILE]`

LO keeps at most 20 candidate memories on disk and offers at most eight to prompt attention. Importance is 0–100; unused memories decay during maintenance. Retrieval alone is not reinforcement. `skills.md` is separate from user memory.


## Profile
`lk profile` · `lk profile files`

`lk profile backup [DEST] [--keep N]` — remember a backup root and create rotating timestamped snapshots.

`lk profile export [ZIP]` — create one portable migration archive.

`lk profile restore SOURCE [--yes]` — restore a compatible ZIP/backup directory after validation; LOOK creates a local safety snapshot first.

Portable profile data includes memory, recent continuity, core, skills, personalities, AI behavior preferences, preferred model name, and feedback settings. Secrets, undo/trash, jobs/events, queues/locks/PIDs, caches, and machine-specific host configuration are excluded.

## Feedback
`lk feedback` · `lk feedback demo`

`lk feedback sound on|off` · `lk sound`

`lk feedback motion off|subtle|normal`

Sound defaults off. Motion defaults subtle. Feedback is automatically silent/static outside a TTY.

## Unified settings
`lk settings` — access profile, Ollama host, preferred model, web-search key, tailnet share, feedback, and profile status. It is a UI over the direct commands above.

## System
`lk home` · `lk doctor` · `lk config` · `lk secrets` · `lk undo` · `lk uninstall` · `lk version` · `lk help`

## File actions
`lcp` · `lmv` · `lscp` · `lrm` · `lmk` · `mkd`

### `lmk` — LOOK make
`lmk FILE.ext` creates an undoable empty file.

`lmk DIR/` creates an undoable directory and enters it.

`lmk -f NAME` forces file creation; `lmk -d NAME` forces directory creation + enter.

Extensionless ambiguous names prompt for `[d]irectory` or `[f]ile`. The ambiguity prompt is single-key; no Return is required. Missing parent directories for a file are created only after confirmation.

`mkd DIR` is a compatibility wrapper for `lmk -d DIR`.

`lk undo` removes an unchanged empty file or an empty created directory; it refuses once the path has meaningful contents or changes.

## Shortcuts
`l/ls` · `ll` · `ld` · `lf` · `lt` · `lr` · `lz` · `zll` · `cdl` · `f` · `lh` · `lo` · `rs` · `rb` · `webterm`

## Completion
`lk <Tab>` completes LOOK commands contextually. `lmk <Tab>` completes explicit mode flags and existing parent directories for a new path. `lk ollama`, `lk memory`, and `lk skills` expose their subcommands; `lk ollama host` includes saved host names. `lo` completes access flags and `@host` choices, then leaves prompt text unconstrained.

## Media
`lk media` · `lk media toggle` · `lk media next` · `lk media prev` · `lk media stop`

Every successful transport action reports the resulting player state/track. macOS controls an already-open Music or Spotify instance; Linux uses MPRIS via `playerctl`.

## Intelligence versions
`lk skills version` shows the installed skills schema, bundled pack version, and learned-skill count.

`lk skills update [FILE]` refreshes Bundled craft from the built-in pack or a compatible external pack while preserving Learned craft.

Memory JSON uses schema version 1.

## Fast media aliases
`mm` → `lk media toggle` · `mn` → `lk media next` · `mp` → `lk media prev`

`lk memory` and `lk skills` use LOOK's pager for readable long output.


## LO personality + thinking

- `lk personality` — list personality packs.
- `lk personality lo|robot|max|philosopher` — select one.
- `lk thinking light|adaptive|deep` — select reasoning depth.
- `lk think-display compact|full|quiet` — select live thinking presentation.
- `lk settings` — configure these alongside access, host, model, and web search.

Bundled personality packs live under `~/.local/share/look/personalities/`. Capability, personality, model, thinking depth, and thinking display remain independent settings.
