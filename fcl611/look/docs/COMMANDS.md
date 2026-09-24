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

`lk skills` · `lk skills add TEXT` · `lk skills forget TEXT` · `lk skills clear-learned` · `lk skills path` · `lk skills state` · `lk skills export [FILE]`

LO keeps at most 20 candidate memories on disk and offers at most eight to prompt attention. Importance is 0–100; unused memories decay during maintenance. Retrieval alone is not reinforcement. `skills.md` is separate from user memory.


## Profile
`lk profile` · `lk profile files`

`lk profile backup [DEST] [--keep N]` — remember a backup root and create rotating timestamped snapshots.

`lk profile export [ZIP]` — create one portable migration archive.

`lk profile restore SOURCE [--yes]` — restore a compatible ZIP/backup directory after validation; LOOK creates a local safety snapshot first.

Portable profile data includes memory, recent continuity, core, skills, personalities, AI behavior preferences, and feedback settings. Secrets, undo/trash, jobs/events, queues/locks/PIDs, caches, and machine-specific Ollama host/model configuration are excluded.

## Feedback
`lk feedback` · `lk feedback demo`

`lk feedback sound on|off` · `lk sound`

`lk feedback motion off|subtle|normal`

Sound defaults off. Motion defaults subtle. Feedback is automatically silent/static outside a TTY.


## Fabric dashboard
`lk dash` — live operational cockpit over the resident Fabric APIs. Shows node health, peer/model activity, trust basis, active jobs, control-plane pressure, managed services, and recent Fabric events. Read-only by default; `r` offers a confirmed restart for named Fabric-managed services. `w` enters `lk fabric watch`, `s` opens settings, and `d` runs doctor.

## Unified settings
`lk settings` — access profile, local preferred model, Fabric routing, legacy direct Ollama host/model, web-search key, tailnet share, feedback, and profile status. `lk models` is always local; `lk ollama models` follows the selected legacy direct host.

## System
`lk doctor island` — loopback-only one-node autonomy audit: deterministic LOOK, local Ollama models, local memory/media, and optional local OpenJev. It does not require Tailscale or a remote Fabric node.

`lk home` · `lk doctor` · `lk doctor island` · `lk config` · `lk secrets` · `lk undo` · `lk uninstall` · `lk version` · `lk help`

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
`lk player` · `lk media` · `lk media browse [QUERY]` · `lk media find QUERY` · `lk media fabric` · `lk media outputs` · `lk media on NODE play TARGET|toggle|next|prev|stop|state` · `lk media identify QUERY|PATH|--all` · `lk media play TARGET [--shuffle]` · `lk media queue` · `lk media scan ROOT` · `lk media library` · `lk media artists` · `lk media albums` · `lk media save NAME` · `lk media load NAME` · `lk media playlists` · `lk media repeat [off|all]` · `lk media state` · `lk media jump INDEX` · `lk media stream PATH` · `lk media add PATH` · `lk media info [@NODE] DIGEST`

Every successful transport action reports the resulting player state/track. macOS controls an already-open Music or Spotify instance; Linux uses MPRIS via `playerctl`.

## Intelligence versions
`lk skills version` shows the installed skills schema, bundled pack version, and learned-skill count.

`lk skills update [FILE]` refreshes Bundled craft from the built-in pack or a compatible external pack while preserving Learned craft.

Memory JSON uses schema version 1.

Node-scoped playback: `lk media outputs` lists reachable Fabric playback endpoints. `lk media on NODE play TARGET` starts a queue on that node; transport/state actions use the same form. Each node owns its local mpv/output session while Fabric keeps queue identity portable between outputs.

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


## Learning feedback
Clear positive/negative conversational feedback may trigger background reflection on the preceding interaction. `lk skills state` shows reinforced learned-skill metadata. This is weak supervision: ambiguous feedback produces no update.


## Living AI
`lk ai` — AI control surface; now includes broker state.

`lk ai status` · `lk ai start` · `lk ai stop` · `lk ai wake` — inspect/control the resident background coordinator.

The broker coordinates `lo bg`, memory maintenance, and skill reflection. Interactive LO turns have foreground priority.

## Fabric File Catalog

`lk scan [ROOT]` refreshes cheap metadata only (path, name, extension, size, modified time). A bare scan catalogs the user home with conservative exclusions. `lk catalog` shows local coverage. `lk find QUERY` searches the reachable Fabric catalog and falls back to the local catalog offline; examples: `lk find Portland schools pdf`, `lk find python yesterday`, `lk find largest zip`.

### Content search (5.7)

The file catalog incrementally extracts bounded text from common text/source/config files, HTML, DOCX, EPUB, and text-bearing PDFs into SQLite FTS5. `lk find` searches names, paths, and indexed contents locally or across Fabric. Results include a short content snippet when FTS matched. Indexing performs no OCR, embeddings, model calls, or hashing.

## Fabric identity and endpoint authorization

`lk fabric identity` — show this node's stable Fabric identity and fingerprint.

`lk fabric pair-code [URL]` — open a five-minute, one-use node pairing invitation. The primary path is the short eight-digit code: on the other machine run `lk fabric pair NODE CODE`. If `qrencode` is installed, LOOK also renders a QR courier containing the node/code/endpoint.

`lk fabric trust` — list trusted nodes. `AUTH` means the peer has a 6.0 authorization credential; `RE-PAIR` means an older trust record must be paired again.

`lk fabric transport` — show local Tailcat endpoints and the active transport selected for reachable peers. Tailcat direct TLS is preferred; Tailscale is fallback.

`lk fabric endpoints` — list pending, temporary, and trusted browser endpoints across the reachable Fabric, grouped by the node that owns them.

`lk fabric allow CODE once|trust` — approve a six-digit browser request temporarily or as a trusted device. The command searches reachable trusted nodes and applies the approval on the node hosting that browser.

`lk fabric endpoint-code URL [once|trust]` — mint a one-use Signal/browser invitation; with `qrencode`, scan it directly with an iPhone camera.

`lk fabric revoke-endpoint ENDPOINT_ID` — revoke a browser endpoint credential wherever it lives in the reachable Fabric.
