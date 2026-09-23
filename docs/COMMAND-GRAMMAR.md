# LOOK Command Grammar — 5.7.2

Generated from the canonical `_COMMANDS` registry. Short aliases are ergonomic entry points; they are not separate implementations.

| Command | Arguments | Area | Purpose |
|---|---|---|---|
| `lk` | `` | files | Open interactive LOOK in the current directory |
| `l` | `[PATH|WORD]` | files | Smart jump + interactive LOOK |
| `ll` | `[PATH|WORD]` | files | LOOK detail view (alias/equivalent: `lk detail`) |
| `ld` | `[PATH|WORD]` | files | LOOK directories (alias/equivalent: `lk dirs`) |
| `lf` | `[PATH|WORD]` | files | LOOK files (alias/equivalent: `lk files`) |
| `lt` | `[PATH|WORD]` | files | LOOK tree (alias/equivalent: `lk tree`) |
| `lr` | `[PATH|WORD]` | files | LOOK recent (alias/equivalent: `lk recent`) |
| `lz` | `[PATH|WORD]` | files | LOOK sizes (alias/equivalent: `lk size`) |
| `zll` | `<WORD>` | files | Zoxide jump + LOOK |
| `cdl` | `<WORD>` | files | Zoxide jump + detail LOOK |
| `ff` | `[WORD]` | files | Global LOOK search |
| `fznv` | `[WORD]` | files | Global LOOK search + Neovim |
| `lk detail` | `[PATH]` | files | Interactive detail view |
| `lk dirs` | `[PATH]` | files | Interactive directories view |
| `lk files` | `[PATH]` | files | Interactive files view |
| `lk tree` | `[PATH]` | files | Interactive tree view |
| `lk recent` | `[PATH]` | files | Interactive recent view |
| `lk size` | `[PATH]` | files | Interactive size view |
| `lmv` | `<SRC...> <DEST>` | files | Move path(s) |
| `lcp` | `<SRC...> <DEST>` | files | Copy path(s) |
| `lscp` | `<SRC...> <DEST>` | files | Copy path(s), preserving source |
| `lmk` | `<PATH>` | files | Smart make file or directory |
| `mkd` | `<PATH>` | files | Make directory |
| `lrm` | `<PATH...>` | files | Remove through LOOK |
| `lk match` | `<TEXT>` | files | Match/find filesystem content |
| `lk open` | `<PATH>` | files | Open in desktop application |
| `lk preview` | `<PATH>` | files | Preview outside terminal |
| `lk reveal` | `<PATH>` | files | Reveal in Finder/file manager |
| `lk undo` | `` | files | Undo newest ready filesystem action |
| `lk undo list` | `` | files | Inspect undo history |
| `lk undo skip` | `` | files | Abandon newest blocked undo record |
| `lk receipts` | `[N]` | files | Inspect transaction receipts |
| `lk system` | `` | system | System control surface |
| `lk doctor` | `` | system | Run LOOK diagnostics |
| `lk doctor island` | `` | system | Audit single-node offline autonomy |
| `lk machine` | `` | system | Machine summary (alias/equivalent: `lk box`) |
| `lk disk` | `` | system | Disk/storage inspection |
| `lk gpu` | `` | system | GPU inspection |
| `lk up` | `` | system | Listening services/ports (alias/equivalent: `lk ports`) |
| `lk port` | `<NUMBER>` | system | Inspect a port |
| `lk processes` | `` | system | Process list (alias/equivalent: `lk procs`) |
| `lk process` | `<NAME>` | system | Inspect process (alias/equivalent: `lk proc`) |
| `lk pid` | `<NUMBER>` | system | Inspect PID |
| `lk git` | `[PATH]` | system | Git repository inspection |
| `lk run` | `[PATH]` | system | Inspect runnable project (alias/equivalent: `lk project`) |
| `lk env` | `` | system | Environment inspection |
| `lk path` | `` | system | PATH inspection |
| `lk why` | `<COMMAND>` | system | Explain command resolution |
| `lk net` | `` | network | Network control surface |
| `lk network` | `` | network | Network inspection |
| `lk tailscale` | `` | network | Tailscale inspection |
| `lk share` | `[...]` | network | Sharing controls |
| `lk services` | `` | network | Service inspection |
| `lo` | `[PROMPT]` | ai | Talk to LO |
| `lo` | `search [PROMPT]` | ai | LO with explicit web search |
| `lk ai` | `` | ai | AI control surface |
| `lk models` | `[MODEL]` | ai | Model chooser |
| `lk benchmark` | `[--all]` | ai | Benchmark model(s) |
| `lk ollama` | `` | ai | Ollama inspection |
| `lk ollama models` | `[MODEL]` | ai | Ollama model chooser |
| `lk ollama test` | `[--all]` | ai | Ollama benchmark |
| `lk ollama host` | `[...]` | ai | Inference hosts |
| `lk ollama share` | `[...]` | ai | Tailnet Ollama sharing |
| `lk ollama access` | `[...]` | ai | LO access profile |
| `lk ollama key` | `[...]` | ai | Web-search key/status |
| `lk ai-pool` | `[...]` | ai | Inference pool |
| `lk access` | `[...]` | ai | Filesystem grants/access |
| `lk personality` | `[...]` | ai | LO personality |
| `lk thinking` | `[...]` | ai | LO thinking mode |
| `lk think-display` | `[...]` | ai | Thinking display |
| `lk memory` | `[...]` | ai | LO memory |
| `lk skills` | `[...]` | ai | LO learned skills |
| `lk profile` | `[...]` | ai | Portable LOOK/LO profile |
| `lk feedback` | `[...]` | ai | LO feedback/expression |
| `lk sound` | `[...]` | ai | Sound feedback |
| `lk vision` | `<IMAGE> [QUESTION]` | ai | Inspect image with vision model |
| `lk generate` | `<PROMPT>` | ai | Generate image through ComfyUI (alias/equivalent: `lk image`) |
| `lk comfy` | `[...]` | ai | ComfyUI discovery/configuration |
| `lk schedule` | `[...]` | ai | Delayed/recurring LO jobs (alias/equivalent: `lk scheduler`) |
| `lk translate` | `[...]` | ai | Translation helper |
| `lk clean` | `` | system | Conservative maintenance surface |
| `lk web` | `[...]` | ai | Web-search key/status |
| `lk budget` | `[...]` | ai | LO context/token budget |
| `lk media` | `[...]` | media | Media controls (alias/equivalent: `lk music`); `state` exposes renderer JSON and `jump INDEX` selects an exact queue row |
| `mm` | `` | media | Toggle media playback (alias/equivalent: `lk media toggle`) |
| `mn` | `` | media | Next media item (alias/equivalent: `lk media next`) |
| `mp` | `` | media | Previous media item (alias/equivalent: `lk media prev`) |
| `lk jobs` | `` | ai | Inspect background LO jobs |
| `lk events` | `[...]` | ai | Inspect LO event stream |
| `lk games` | `` | meta | Game availability |
| `lk ttt` | `` | meta | Tic-Tac-Toe easter egg |
| `lk gtnw` | `` | meta | Global Thermonuclear War easter egg |
| `lk settings` | `[SEARCH]` | config | Unified settings |
| `lk config` | `` | config | Configuration surface |
| `lk config paths` | `` | config | Show configuration paths (alias/equivalent: `lk config raw`) |
| `lk apps` | `[...]` | config | Desktop app preferences |
| `lk shortcuts` | `[...]` | config | Shell shortcut policy |
| `lk secrets` | `` | config | Inspect secret-file status |
| `lk home` | `` | config | LOOK home |
| `lk help` | `` | meta | Starter help |
| `lk help all` | `` | meta | Complete glossary |
| `lk commands` | `` | meta | Interactive command palette |
| `lk architecture-audit` | `` | dev | Architecture self-audit |
| `lk tooling-audit` | `` | dev | Tool harness self-audit |
| `lk command-audit` | `` | dev | Canonical command grammar audit |
| `lk locator-test` | `` | dev | Locator self-test |
| `lk version` | `` | meta | Print LOOK version |
| `lk uninstall` | `` | meta | Uninstall LOOK |

## Interactive LOOK grammar

Current renderer keys to audit across normal, filter, selected, and marked states:

- Typing: live filter; multiple words narrow matches.
- `J/K` or arrows: move selection.
- `Tab`: mark/unmark; `A`: mark all matches; `X`: clear marked set.
- `Enter/→`: open file or descend directory.
- `C`: Copy To; `M`: Move To; `R`: remove.
- `B`: file clipboard; `Y`: copy path; `E`: edit; `O`: open with.
- `L`: send selected path(s) to LO context.
- `G`: request shell go-to for selected directory; `←`: parent.
- `Esc`: clear/back/cancel according to state; `q`: quit where applicable.

## Audit rule

`lk` and every explicit LOOK view mode are interactive on a TTY regardless of whether the directory fits on one screen. Output size controls scrolling, not capability.

## Node-scoped media output

`lk media outputs` discovers reachable playback endpoints. `lk media on NODE play TARGET` and transport variants route to one node-specific MediaSession/output. Signal uses the same routing surface; changing output can hand the queue/current index to another node.

## File catalog

```text
lk scan [ROOT]
lk catalog
lk find QUERY
fcl-node file-catalog [--node NODE] [--json]
```

`scan` is metadata-only. A bare scan uses the home directory with conservative exclusions. `find` prefers the reachable Fabric union and falls back locally; cataloging never grants access or transfers bytes.

### Content-search behavior

`lk scan [ROOT]` incrementally indexes bounded deterministic text for supported documents. `lk find QUERY` combines metadata and FTS5 content results; remote nodes execute their own search and return bounded matches rather than transferring the index. Unsupported, oversized, image-only, or unextractable files remain metadata-searchable.
