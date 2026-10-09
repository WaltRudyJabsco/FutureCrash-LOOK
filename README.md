# Future Crash + LOOK 8.12.0 — FABRIC MEDIA

8.12.0 adds an inline Notebook view: Enter reads, E makes a quick edit, and V
opens the full editor. Named notes reopen directly in this lightweight view.

8.11.0 adds reusable notes by title, creation/edit timestamps, sort and type
cycling, distinct title filtering and full-text search, and friendlier reminder
durations. Future Crash footer keys now use cyan accents.
8.10.2 isolates Future Crash's shared LO output from the live terminal, protects
Escape from late replies, and adds notebook H/? help plus offline per-command
help. Start with [Finding help](docs/HELP-GUIDE.md).
8.10.1 fixes notebook screen clearing, adds multiline quick capture with
Enter to save and Shift-Enter to insert a newline, and gives LO explicit
notebook list/read tools plus direct handling of simple notebook questions.
8.10.0 adds the replicated LOOK notebook: `lkn` / `lk notes`, `lk tasks`, and
`lk reminders`. Capture and edit Markdown offline, file records by project,
and synchronize revisions across paired nodes. Due reminders appear in Albert
and Signal with Done, Snooze, and Open note controls. Future Crash's workstation
keeps Escape responsive during host operations. See [Notebook guide](docs/NOTEBOOK.md).

8.12.0 stabilizes the Phase-2 refactor and hardens Fabric media across nodes: faster catalog discovery, reliable remote playback, browser handoff by media ownership, remote artwork and previews, removable-media wake-up, and cleaner LOOK filter interaction.

**One local-first personal computer made from the machines you already own.**

Remote and local media covers now use the same explicit full-RGB Chafa symbol contract. The media-owning node renders remote cover art and returns only terminal rows; Player and Media Find paint those rows directly without storing preview images on endpoint disks.

8.5.0 established the stabilization baseline: shared Media Find/Player artwork rendering, audited help/man/docs, and independent component version identities.

| Layer | Version |
| --- | ---: |
| Future Crash + LOOK bundle | **8.12.0** |
| LOOK component | **4.59.0** |
| Future Crash component | **1.2.5** |

Use `lk version` for installed LOOK/bundle identity, `lk help` for the starter map, `lk commands` for the searchable index, `lk doc` / `lk help all` / `man lk` for the full reference, and `lk tldr` for short examples. Component versions intentionally advance independently.

Download videos directly on a chosen Fabric node with `lk ytd URL --node 3090`. The installer includes yt-dlp and ffmpeg. See [Fabric downloads and descriptions](docs/fabric-downloads.md) for progress, search, optional holding, Keep, catalog freshness, and dated forecasts.

## Current high-value workflows

- `l` / `lk PATH`: interactive LOOK browser. Arrow navigation enters the filter/focus view; Tab marks; Shift-arrow navigation keeps fast top/page/bottom movement.
- `C` / `M`: Copy To / Move To with editable destination plus directory picker.
- `Shift-D`: remove selected/marked objects with confirmation and journaled undo where supported.
- `Shift-R`: rename one or many objects; `#`, `##`, `###` provide numbered batch patterns.
- `lk media find QUERY`: Fabric media selector with local or owner-rendered remote terminal artwork; navigation repaints without clear-to-blank flashes.
- `lk player`: live queue/player with terminal artwork, EQ activity view, transport controls, `s` shuffle, and `r` repeat.
- `lk mp`: integrated Fabric media workspace: searchable library, queue, art/info, now playing, and transport in one terminal surface.
- Remote Fabric previews follow the same owner/id routing already proven by playback; the owning node renders Chafa and returns only the terminal preview rows.

---

## Historical release notes preserved below

# Future Crash + LOOK 7.7.8 — MEDIA SESSION

7.7.8 MEDIA SESSION preserves `V` Preview View to the stable 7.6.4 SIMPLE PREVIEW lineage. In a filtered list, `V` toggles a full-content preview of the same working set; arrows navigate the same selection, Space/Tab use the existing marked set, and Esc/V returns to the same filtered list. ASCII/Chafa remains the immediate canonical preview. On macOS iTerm2 and Linux Kitty, Preview View and the ordinary wide side preview can progressively overlay their known art rectangles with native images prepared off-thread; unsupported terminals and failures remain ASCII, and the worker never paints or drives pager state.

## Inherited baseline: 7.6.4 — SIMPLE PREVIEW

7.6.4 deliberately restores LOOK's 7.5.7 pager architecture after the native terminal-graphics experiment destabilized filtering and navigation. Image and PDF previews are ordinary Chafa symbol rows composed synchronously into the filtered frame. There are no Kitty/iTerm/Sixel graphics payloads, preview workers, preview timers, or asynchronous terminal painting in LOOK. Existing Auto/Graphics preview preferences migrate safely to ASCII; the settings surface now exposes only ASCII or Off.


7.6.4 fixes default-voice audition semantics and introduces typed, endpoint-aware Fabric attention routing. Explicit alerts can target the origin node, a named node/browser endpoint, or all current speech-capable endpoints; active/follow-me targeting remains deliberately unresolved until trustworthy presence evidence exists.

# Future Crash + LOOK 7.3.0 — LIVE STATE

7.3.0 separates present-tense machine state from durable memory/history. A bounded Live State layer keeps typed objects such as terminal windows fresh, records provenance and age, retires objects when authoritative evidence says they are gone, and hands JEV/cognition only the state slice relevant to the current request. Receipts update the scene automatically; `lk state` is an inspection/debugging surface, not a configuration requirement. This is the first explicit implementation of the spinning-plates model: skills and procedures can persist, while layouts, processes, referents, and other current facts stay refreshable and disposable.

# Future Crash + LOOK 7.2.0 — CAPABILITY CURATOR

7.2.0 makes host capability discovery automatic. Each node non-destructively inspects its available OS/application adapters, persists a typed capability catalog, advertises those capabilities to Fabric, and upgrades adapters from discovered to proven through real successful receipts. JEV referential actions now include maximize, full screen, focus, and minimize as well as close. Linux terminal launches carry a zero-dependency control channel and stable window token, with stronger `wmctrl`/`xdotool` adapters preferred when present; macOS uses Terminal/AppleScript handles. `lk capabilities` exists for inspection/debugging, but install and normal operation curate automatically.

# Future Crash + LOOK 7.1.0 — JEV FABRIC

7.1.0 makes JEV a node-level cognition layer. JEV-0 deterministic trees ship on every node and own obvious semantic structure before general cognition; JEV-1 uses the existing OpenJev worker as an optional local learned judgment tier, auto-provisioned on capable nodes and managed on Linux/macOS. Explicit image generation now owns its descriptive payload so words such as `rain` cannot hijack the turn into weather. Typed-referent JEV normalizes conversational glue/self-address and resolves bounded unique aliases such as `and close it`, `lo close that window`, and `close ascii`. Ambiguous residue still escalates rather than being guessed.

# Future Crash + LOOK 7.0.5 — TYPED REFERENTS

7.0.5 makes host-created UI objects first-class referents. A command launched in a new terminal now records a typed `terminal_window` handle in authoritative world-state receipts. JEV can resolve follow-ups such as `can you close that window`, `close it`, and `close that` against a single compatible recent object and dispatch a dedicated `close_object` primitive before model cognition. Linux terminal sessions record the PID of the process running inside the spawned terminal; macOS records the Terminal window ID. Ambiguous referents fall through rather than being guessed.

# Future Crash + LOOK 7.0.4 — JEV WIRED

7.0.4 fixes the installed-layout contract for the JEV command tree introduced in 7.0.3. The unified installer now ships `core/jev.py`, verifies the installed copy byte-for-byte, and includes JEV in the post-install runtime import check. A dedicated regression stages only the installed core path and proves LOOK can resolve `run asciiquarium in new terminal` with no source checkout available.

# Future Crash + LOOK 7.0.3 — JEV TREES

7.0.3 turns the 7.0.2 action reflex into the first reusable JEV judgment tree. Explicit command language is decomposed into typed command payload plus host-owned execution modifiers before any shell action: `again` is retry semantics, `in the terminal` is current-terminal presentation, and `in a new terminal` is asynchronous new-terminal presentation. One-token RUN payloads fast-path; multi-token payloads must have a resolvable executable head or fall back to cognition instead of becoming accidental argv.

The command tree lives in `core/jev.py`, separate from LOOK execution. Surfaces provide edge facts such as PATH resolution; JEV returns a typed decision; current access/risk policy still owns authorization and execution.

# Future Crash + LOOK 7.0.2 — ACTION REFLEX

7.0.2 keeps 7.0.1's authority model and moves explicit execution ahead of deliberative cognition. Clear `run/launch/execute/start` commands and recent typed retries are resolved at the host edge, rechecked against current authority, executed, and only then explained. Persistent memory can inform an action but can no longer veto a fresh operator imperative.

# Future Crash + LOOK


### 7.0.0 · WORLD STATE

7.0.0 moves LO from conversation-centered tool use toward a persistent operating intelligence. Language proposes; deterministic edges act; typed receipts establish truth; task graphs and wake state survive model/session boundaries.

The new `world_state.json` records active goals, bounded task steps, action preflight policy, typed receipts, classified failures, and wake events. `lk world` exposes that state directly. Consequential actions pass through a structural deliberate/verify-required policy while read-only actions remain cheap.

A real regression drove the design: `run asciiquarium in the terminal` crashed because `_looks_like_shell_file_discovery` was referenced but undefined, and a later model turn paraphrased the failure incorrectly. 7.0.0 restores the guard, records the exact host failure, and answers later tool-error questions directly from the receipt instead of asking a model to remember what happened.



### 6.9.4 · LOOK FIT & FINISH

6.9.4 restores the core interactive LOOK invariant: one candidate is one visible row. It also layers Copy/Cut/Paste staging over LOOK's existing marked-selection, native clipboard, `_batch` transaction, rollback, and `lk undo` machinery.
## 6.9.0 · COGNITIVE FABRIC

6.9.0 closes the loop between model evidence, deterministic primitives, receipts, memory and persistent goals. Speech and explicit remembering require real host receipts; model tests now include LOOK-specific Fabric Fit; named model sets preserve good configurations as champion/challenger experiments; and shared cognition carries explicit evidence authority plus wake/close semantics for durable goals.

Useful model-set commands:

```text
lk ollama set list
lk ollama set save NAME
lk ollama set show NAME
lk ollama set champion NAME
lk ollama set challenger NAME
lk ollama set compare A B
lk ollama set apply NAME [reflex|balanced|deep]
```

Tailcat/Tailscale transport is intentionally unchanged in this release.

## 6.7.1 · HOME BASE

HOME BASE fixes a working-state failure exposed by ordinary weather conversation. When LO asks for a location, the next short answer is now owned by that pending goal instead of being reinterpreted as a fresh prompt. Literal `home` is never sent to a public geocoder; an explicit statement such as `my home is Portland OR` becomes a typed, replaceable semantic preference and is reused by `home` / `my weather`.

Current-weather answers are also rendered directly from the canonical WEATHER receipt, so a successful lookup cannot end in `(no final response)` or be reconstructed incorrectly by the language model. This release intentionally leaves the 6.7 BEACON networking architecture unchanged.

## 6.7.0 · BEACON

BEACON begins Fabric's independent Internet discovery layer. Already-paired nodes can optionally announce short-lived, Ed25519-signed presence through a tiny public rendezvous service. Pairwise authorization tokens stay on the devices; only one-way capability slots are published. Resolved addresses become temporary Tailcat candidates while the certificate pinned during pairing remains the authority.

This is deliberately the first networking stage, not a fake Tailscale replacement: 6.7.0 adds secure rendezvous but leaves UDP hole punching and encrypted relay for the next stages. Tailscale remains a fallback while those pieces are built.

Also includes the 6.6.5 native mpv video fix, SHOWTIME startup receipts, MOVIE NIGHT selector normalization, TRUE CURSOR terminal editing, ONE BRAIN cognition, and LIVING MIND memory.

**One personal computer made from the machines you already own.**

Future Crash + LOOK is a local-first terminal environment and personal computing Fabric. LOOK is the practical interface, LO is the conversational interface, Future Crash is the ambient workstation, and Fabric lets machines contribute files, models, services, media, sensors, and outputs without turning any one machine into a mandatory server.

```text
one node  = a complete system
more nodes = the same system with more capabilities
```

A laptop can work alone on an airplane. Reconnect it and larger models, indexed files, media, web search, and other capabilities on your workstation become available again.

![Future Crash](FC_screenshots/Error_2.png)

## What it does

- **LOOK (`lk`)** — navigation, filtering, file operations, machine inspection, catalogs, media, models, memory, Fabric controls and small terminal utilities.
- **LO (`lo`)** — conversation plus explicit tools. LO interprets intent; LOOK resolves resources; deterministic commands do the work.
- **Future Crash** — the terminal/workstation personality and ambient interface over the same underlying system.
- **Fabric** — capability discovery and routing across trusted personal machines. Nodes advertise what they can actually do rather than pretending every machine is identical.
- **Signal** — browser endpoint for conversation, camera input, visual output and media control. A browser is an endpoint, not automatically a compute node.

![LOOK file filter](FC_screenshots/LOOK_Shell_filter_find.png)

## Install

macOS and Linux are the primary targets. Clone or unpack the release and run:

```sh
./install.sh
```

Then open a new shell and start with:

```sh
lk doctor
lk machine
lk
lo
future-crash
```

The installer is intentionally additive. Optional capabilities degrade cleanly when their dependencies are absent.

## Playback controls, prompt recall, and remote maintenance

The reference terminal is **Kitty on both macOS and Linux**; **mpv** remains the
canonical local/Fabric playback engine. VLC is an optional standalone player.
Activate the bundled terminal profile with `./install.sh --kitty`. This explicitly
checks/installs Kitty and backs up any existing `~/.config/kitty/kitty.conf` before
replacing it. Ordinary installs leave your terminal configuration alone. To apply
just the profile to an already-installed Kitty, run `python3 tools/configure_kitty.py`.
Personal overrides live in `~/.config/kitty/kitty-local.conf`, loaded last.

The profile uses a transparent green phosphor theme (82% opacity, blur radius 24),
a moving cursor trail, powerline tabs, MesloLGS NF at 13pt, and ordinary ANSI
colors for art and diagnostics, and the OS login shell. Both Mac Option keys work
as Alt. Shift-arrows and Ctrl-R go to LOOK/LO; terminal shortcuts use Control-Shift
(with conventional Command shortcuts on Mac). Use Control-Shift-PageUp/PageDown
for terminal scrollback, Control-Tab to cycle tabs, and Control-Shift-T/N for a new
tab/window in the same directory. Fully restart Kitty after changing Option keys.
Use Control-Shift-A then M/L to increase/decrease opacity, or R to reset.
Blur depends on the desktop compositor on Linux. The installer supplies the matching Meslo font on Mac; on Linux install it locally
or set `font_family` in the personal override. Remote runtime updates do not deploy
terminal preferences or install applications/fonts.

Signal's player displays ASCII album art by default. Choose **ASCII**, **Image**, or
**Art off** on the player card, or use `/art ascii`, `/art image` (also
`/art high-res`), or `/art off`. The browser remembers your choice. Image mode
shows the original cover supplied by the media owner; it does not upscale it.
Cover extraction and transport use the existing Fabric cover endpoint, and missing
art never blocks playback. Browser Now Playing metadata receives the original
cover independently of the in-page art style.

Signal registers browser Media Session controls while playing on **This Device**:
play/pause, previous/next, seeking, and Now Playing metadata. Moving playback to
another node releases the browser's media session. Hardware delivery, especially
CarPlay steering-wheel controls, should be checked on the actual device.

LO uses the terminal line editor's Up/Down history, Left/Right editing, and Ctrl-R
search. Submitted prompts persist on that device in `~/.local/share/look/lo_history.json`.
Recall uses the current resource context and never runs a recalled command until
Enter. Responses, pixels, and attachment payloads are not stored in prompt history.

Install this update normally **once on each participating node** to bootstrap the
maintenance protocol. Afterward a node with a freshly installed runtime can serve
its registered code to paired peers:

```sh
lk fabric release m3max-pro
lk fabric update m3max-pro 3090 m4-air
lk fabric maintenance 3090
lk fabric service 3090 node restart
```

`update SOURCE TARGET...` displays the exact source commit and bundle digest for
approval; `--yes` provides explicit unattended approval. `TARGET=all` selects the
advertising peers plus the local node, excluding the source. Offline or older
nodes report an error; they are not silently assumed updated. The request returns
a job ID; `maintenance NODE [JOB_ID]` reports staged, draining, installing,
restarting, verifying, healthy, rolled_back, or failed. A healthy receipt confirms
the installed bundle digest and local node health, not merely file transfer.

Updates validate paths, file hashes, size limits, and Python syntax before any
replacement. They wait up to five minutes for inference/native playback and
active media streams, preserve the old runtime, stop affected services, replace
code, and restart. Failed health verification restores the old files. Node
restart is explicit and immediate, so it can recover a stuck inference lease.
The helper runs separately from the node and keeps receipts and backups under
`~/.local/share/future-crash-look/maintenance`.

This is an explicit **runtime code update**, using authenticated paired-peer
transport and an operator-approved digest. It does not install dependencies,
change service definitions or shell configuration, update models, reboot hosts,
or automatically trust whichever node advertises newer code. Changes requiring
those installation steps still use the unified installer. Distribution uses
installed runtime files; it does not advance a target's Git checkout. An open LO
process keeps its imported code until you reopen it; reload Signal after an update.


## Files: discovery first, understanding second

LOOK maintains a cheap local SQLite catalog. A normal scan records filesystem metadata and incrementally extracts bounded text from formats where extraction is deterministic and inexpensive.

```sh
lk scan
lk catalog
lk find "GDP happiness"
lk find "largest pdf"
```

Content search uses SQLite FTS5. Supported sources include text/Markdown, source and common config files, HTML, DOCX, EPUB, and text-bearing PDFs. There are no embeddings, OCR, model calls or mandatory hashes in the basic indexing path.

`lk find` is interactive on a terminal: navigate the ranked matches, inspect evidence, select a result, and hand a locally reachable result into the normal LOOK file workflow. Fabric search stays data-local: each node searches its own catalog and returns bounded matches/snippets rather than shipping its index around the network.

![LOOK AI](FC_screenshots/LOOK_AI.png)

## AI and models

Future Crash + LOOK uses Ollama-compatible local inference. The interface and model do not have to live on the same machine: a small laptop can use its local model while disconnected and use a larger GPU node when Fabric makes one available.

```sh
ollama pull qwen3:8b
lk ollama models
lk ollama host
```

Commercial/cloud model services are optional edges, not architectural requirements.

## Web search: accountless by default

Generic web search now prefers **self-hosted SearXNG**. A node with a healthy SearXNG JSON endpoint advertises the Fabric capability `web.search`; LO on another machine can use that capability without having SearXNG installed locally.

Provider order is deliberately boring:

```text
Fabric SearXNG
    ↓
local SearXNG
    ↓
optional Ollama hosted search
    ↓
offline / unavailable
```

No Ollama account or API key is required for the default self-hosted path. If an `OLLAMA_API_KEY` is already configured, hosted Ollama search remains a fallback.

On a Linux machine using the bundled Local Labs server controller:

```sh
server install searxng
server normalize searxng
server configure searxng
server check searxng-api
server search "Future Crash LOOK"
```

SearXNG is installed as an ordinary system service and remains independently inspectable. LOOK does not hide or replace the underlying Linux service management.

## Fabric

Fabric separates *what a machine can do* from *which machine it is*.

```text
                 FABRIC

 files       models       media       web search
   \            |           |             /
    \           |           |            /
             capabilities
                  |
        choose an appropriate node
                  |
              do the work
```

Useful surfaces include:

```sh
lk fabric
lk fabric nodes
lk fabric events
lk fabric decisions
lk media fabric
fcl-node dash
```

The dashboard is responsive to terminal geometry: wide/short, ordinary, compact and narrow layouts preserve the important state instead of assuming every laptop has the same terminal dimensions.

### Island Mode

Fabric is an extension of a machine, not a dependency of it. Local files, local memory, deterministic LOOK tools and available local inference continue when peers disappear.

```sh
lk doctor island
```

## Fabric identity and accountless pairing

Every node now owns a local **Ed25519 Fabric identity**. The stable node ID and human-readable fingerprint are derived from its public key; the private key stays on that machine. Tailscale names and IP addresses are transport hints, not identity.

```sh
lk fabric identity
lk fabric trust
```

A trusted node can open a one-use five-minute invitation:

```sh
lk fabric pair-code
```

When Tailscale HTTPS is available, LOOK can infer the reachable bootstrap endpoint automatically. The invitation prints an eight-digit, five-minute, one-use code and a simple join command; if `qrencode` is installed it also renders a human-readable QR courier. On the joining node:

```sh
lk fabric pair 3090 48219371
```

Pairing is still bilateral in 6.1: a direct M4↔M3 relationship needs its own pairing even if both machines are already paired with the 3090. Fabric-wide membership sponsorship is a separate trust-topology problem, not part of Tailcat transport.

The nodes exchange public identities, validate the node ID against the public key, record one another in their local trust stores, and consume the invitation. No Fabric account, email address, central identity server, or Tailscale identity is involved.

```text
identity       Fabric Ed25519 keypair + stable node ID
trust          local Fabric trust store
discovery      capabilities and reachable peers
transport      localhost / Tailcat / Tailscale fallback
```

Remote Fabric APIs now enforce paired node authorization. **Tailcat** is the preferred native node-to-node transport when a paired peer is directly reachable: it serves the guarded Fabric API over TLS on port `7443`, pins the peer certificate learned through Fabric trust, and falls back to Tailscale when direct reachability is unavailable. It does not yet attempt NAT traversal or relay traffic; those are later transport layers, not identity work.

Inspect the active path with:

```sh
lk fabric transport
```

## Media and browser endpoints

Media is a reference workload for artifacts, sessions and output routing rather than a separate product silo.

```sh
lk media scan ~/Music
lk media find "Talking Heads"
lk media play "Remain in Light"
lk media outputs
lk player
```

A Signal browser can act as an ephemeral endpoint for display, camera and playback. Media queues and artifact identity belong to Fabric; the browser is simply one possible renderer.

![Machine context](FC_screenshots/PNC.png)

## Permission model

LO separates reasoning from permission.

| Profile | Permission |
| --- | --- |
| Conservative | Read/search and reason; no writes |
| Workspace | Read and intentionally edit inside the starting workspace |
| Power | Workspace tools plus individually confirmed shell commands |
| Unsafe | Unrestricted shell commands with the current user's privileges |

External input is validated at the edges. Dangerous operations stay explicit. A model being capable of proposing an action does not grant permission to perform it.

## Memory and decisions

Fabric Memory is small, inspectable and scoped. Shared/persona memory can replicate among live trusted nodes while node-local memory stays local.

```sh
lk memory
lk memory fabric
lk memory shared
lk skills
```

The Decision Plane treats uncertainty as data. Deterministic rules remain fast; optional learned judgment such as OpenJev can provide bounded evidence; consequential ambiguity can be surfaced to the human without turning the UI into the execution authority.

## Design rules

Future Crash + LOOK tries to stay boring underneath:

- local-first and useful with one machine;
- capabilities instead of machine roles;
- metadata before hashing, lexical search before embeddings;
- work moves to data when that is cheaper than moving data;
- browser endpoints are not automatically trusted compute nodes;
- optional services fail gracefully;
- observable Linux/macOS primitives rather than hidden infrastructure;
- no account should be required merely to make the core system useful.

## Accountless pairing and endpoints

Pair two nodes without copying a long URI:

```sh
# machine A
lk fabric pair-code

# machine B
lk fabric pair 3090 12345678
```

A new Signal browser shows a six-digit authorization code. Approve it from **any reachable trusted Fabric node**; LOOK locates the node that owns the pending browser request and performs the approval there:

```sh
lk fabric endpoints
lk fabric allow 482193 once
lk fabric allow 482193 trust
lk fabric revoke-endpoint ep-...
```

For an iPhone, a trusted machine can mint a one-use browser invitation and render a QR when `qrencode` is available:

```sh
lk fabric endpoint-code https://signal.example trust
```

The browser receives a scoped HttpOnly credential; no Future Crash account, password, or third-party identity provider is involved.

## Documentation

Detailed command help lives in the installed tools and focused docs rather than at the top of this README:

```sh
lk help
lk man
fcl-node --help
server help
```

See `docs/COMMAND-GRAMMAR.md`, `look/docs/COMMANDS.md`, and `docs/RELEASE-HISTORY.md` for the deeper command/release record.

For repository health, run `./tools/verify.sh`; `docs/CODE_HEALTH.md` documents the structural checks and current complexity baseline.

## Historical release note: 6.1.10

The following section describes **6.1.10 — Media Mount Race Repair** and is preserved for release-history context. The current bundle is **8.12.0 — FABRIC MEDIA**.

Browser endpoint management is now Fabric-wide: `lk fabric endpoints`, `allow`, and `revoke-endpoint` work from any reachable trusted node rather than only the Signal host. Tailcat adds direct certificate-pinned TLS transport between paired nodes on reachable LAN/IP paths and is preferred automatically; Tailscale remains a fallback for reachability and bootstrap rather than the definition of Fabric networking. Existing 6.0 pairings learn Tailcat metadata from authenticated peer identity and do not require another re-pair.

Future Crash + LOOK remains an open, local-first project: **Fabric turns your computers and devices into one personal computer; LOOK is how you use it.**


## Albert remote browser access (6.4.0)

Albert stays on localhost. When Tailscale is installed, the installer publishes it through Tailscale Serve on HTTPS port 7330.

```bash
lk albert url      # print iPad/tailnet URL
lk albert qr       # QR if qrencode exists; always prints URL
lk albert ipad     # open the tailnet URL here
```

On an iPad connected to the same tailnet, open the URL printed by `lk albert url` in Safari.


## Albert cognition surface (6.4.3)

Albert is a first-class Fabric UI: synchronized beacon/disco presence, continuing answer-fold conversations, and artifact-aware paste/drop input. Pasted images and files are registered locally and supplied to the shared LO engine by reference rather than embedded into inference packets. Current-news/headline requests are routed through live search/tool evidence when available.


## LOOK Games (6.4.8 · SOUND CHECK)

`lk games` opens the WOPR recreation channel. Board games support `0p`, `1p`, and `2p`: `lk games chess 1p`, `lk games checkers 0p`, `lk games backgammon 2p`, and `lk games ttt 1p`. `lk games gtnw` keeps the Global Thermonuclear War simulation. The old `lk ttt` and `lk gtnw` commands remain aliases.


### 6.4.5 · JOSHUA

`lk games` deliberately reports `No games installed.` The hidden doorway is a named simulation such as `lk games chess` or `lk games gtnw`. On first interactive entry the WOPR recreation channel accepts `JOSHUA` at `LOGON:`; named games then show the simulation selector and player-count chooser. `lk games chess 0p` remains a direct shortcut.

Albert, Signal, and terminal LOOK now share the same host-owned intent gate for obvious game and current-news requests before inference. Surface code controls presentation; it no longer decides whether `gtnw` means a game or whether `headlines` means live web search.


### Fabric speech

Browser-local effects are resolved by the resident Fabric daemon, so endpoint listings and effect routing share the same live registry.

Speech is a routed local effect. Every node with a local synthesizer advertises `audio.speak`; cognition may run elsewhere while the selected endpoint speaks. `fcl-node speak --node NODE TEXT` targets a Fabric node directly, and `lk fabric speak @NODE TEXT` is the human LOOK doorway. The shared LO tool plane can also invoke `audio_speak` for explicit read-aloud and hands-busy notification requests.

The WOPR profile uses the same offline `espeak-ng` + SoX chain on macOS and Linux. macOS `say` is only a graceful fallback. Set `LOOK_GAMES_VOICE=0` to mute game speech.

## LOOK Games — WOPR recreation channel

`lk games` performs the theatrical `LOGON: JOSHUA` ritual, then denies that games are installed. Named simulations (`lk games ttt`, `checkers`, `chess`, `backgammon`, `gtnw`) enter the WOPR selector. Board games support 0p/1p/2p and return to the selector with `q`; `s` stops. WOPR speech is lightweight and offline: macOS uses `say`/Zarvox, Linux uses `espeak-ng` with SoX when available. Set `LOOK_GAMES_VOICE=0` to mute it.

## Current documentation

- `docs/CURRENT-SYSTEM.md` — canonical ownership, ports, queues and invariants.
- `docs/MEDIA.md` — catalog/queue/playlist model and current media controls.
- `docs/ARCHITECTURE.md` — deeper architecture notes.
- `docs/RELEASE-HISTORY.md` — historical record.
