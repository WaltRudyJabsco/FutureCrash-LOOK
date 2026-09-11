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

`lk skills` · `lk skills add TEXT` · `lk skills forget TEXT` · `lk skills clear-learned` · `lk skills path`

LO keeps at most 20 candidate memories on disk and offers at most eight to prompt attention. Importance is 0–100; unused memories decay during maintenance. Retrieval alone is not reinforcement. `skills.md` is separate from user memory.

## Unified settings
`lk settings` — access profile, Ollama host, preferred model, web-search key, and tailnet share. It is a UI over the direct commands above.

## System
`lk home` · `lk doctor` · `lk config` · `lk secrets` · `lk undo` · `lk uninstall` · `lk version` · `lk help`

## File actions
`lcp` · `lmv` · `lscp` · `lrm` · `lmk` · `mkd`

## Shortcuts
`l/ls` · `ll` · `ld` · `lf` · `lt` · `lr` · `lz` · `zll` · `cdl` · `f` · `lh` · `lo` · `rs` · `rb` · `webterm`

## Completion
`lk <Tab>` completes LOOK commands contextually. `lk ollama`, `lk memory`, and `lk skills` expose their subcommands; `lk ollama host` includes saved host names. `lo` completes access flags and `@host` choices, then leaves prompt text unconstrained.

## Media
`lk media` · `lk media toggle` · `lk media next` · `lk media prev` · `lk media stop`

macOS: Music / Spotify adapter. Linux: MPRIS via `playerctl`.

## Intelligence versions
`lk skills version` shows the installed skills schema, bundled pack version, and learned-skill count.

`lk skills update [FILE]` refreshes Bundled craft from the built-in pack or a compatible external pack while preserving Learned craft.

Memory JSON uses schema version 1.
