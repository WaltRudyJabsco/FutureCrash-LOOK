# 5.6.0 — Fabric File Catalog

LOOK now maintains a lightweight SQLite metadata catalog for ordinary files, extending the media-catalog lesson to the rest of the filesystem. `lk scan [ROOT]` records paths, names, extensions, sizes and modification times without reading or hashing file contents; a bare `lk scan` uses the home directory with conservative cache/build/hidden-directory exclusions. `lk catalog` reports local coverage and `lk find QUERY` accepts useful plain-language metadata terms such as `pdf`, `recent`, `yesterday`, and `largest`.

Each Unified Node publishes its local catalog through `/v1/files/catalog`; `/v1/files/fabric` unions currently reachable node catalogs. `lk find` prefers that Fabric union when the node is available and falls back to the local SQLite catalog in Island Mode. Paths remain node-owned metadata: cataloging never grants new filesystem access and never transfers file bytes.

Fresh installs seed the first home metadata scan in the background. Expensive identity, content extraction, FTS and semantic understanding remain deliberately deferred layers rather than costs paid during discovery.

# Future Crash + LOOK 5.6.0

## 5.5.0 — Media Endpoint Handoff

Signal media output routing is now explicit: browser playback is a local browser endpoint and never enters Fabric media-move dispatch, while node-to-node handoff uses the Fabric route. Cross-node queues are rewritten to range-capable source-node stream URLs so a Mac can play a 3090 library without sharing `/srv` paths or copying the track first. Signal uses stable endpoint buttons rather than an iOS native select picker, and node HTTP errors preserve their real diagnostic instead of collapsing to `Fabric media move unavailable`.


## 5.4.9 — Stable Safari Output Picker

Signal media output now has exactly one authoritative target: either `browser` for the current Signal tab or `node:<id>` for a Fabric playback node. Polling observes that target but never chooses it. iOS output handoff no longer rebuilds the native selector while Safari is dismissing its picker, and a node with LOOK + mpv advertises playback capability even before it has a local media session.

Signal's media output selector remains on the active player card. Browser handoff is now transactional: choosing **This Device / This iPhone** immediately claims the card while Safari opens the range-capable audio stream, preventing normal session polling from snapping the chooser back to the 3090. Audio proxies stream chunks as they arrive rather than buffering a whole track before playback begins.

Dash now separates semantic Fabric activity from local renderer effects. Beacon/RGB/pulse frames no longer fill RECENT, ANSI arrow/mouse/scroll sequences are consumed before hotkey dispatch (notably arrow-down's `ESC [ B`), and the beacon key is rate-limited against key repeat.


## 5.4.6 — Endpoint Media Cleanup

Signal keeps **OUT** on the active media card instead of cluttering the chat composer. The card can hand the current session among playback-ready Fabric nodes or to an ephemeral **This Device** browser endpoint; iPhone Safari labels that endpoint **This iPhone**. Browsers remain lightweight UI/media endpoints rather than full compute nodes.

`mpv` is now a standard LOOK workstation dependency. Fresh installs and upgrades install it automatically when missing, so Macs advertise usable playback after upgrade instead of appearing grey with no explanation. Disabled node choices now carry the concrete reason, such as `mpv missing`.

## 5.4.5 — Node-Scoped Media Outputs

Media playback is now explicitly **session + output** rather than one accidental machine-global player. Every reachable Fabric node advertises a default `media.playback` endpoint, Signal has a compact **OUT** chooser, and direct requests such as `play talking heads` are routed to the selected node. Each node keeps its own LOOK MediaSession/queue and local playback worker.

Changing Signal's output while a session is active moves the canonical queue/current index to the target node, starts playback there, and then stops the source node. Queue entries remain Fabric references; remote bytes are streamed/identified through the existing artifact layer rather than copied into Signal.

New deterministic surfaces:

```text
lk media outputs
lk media on M4-Air play "Talking Heads"
lk media on 3090 next
```

The camera composer also gets the small iPhone fix: after accepting a photo, `what am I looking at?` is now real selected input text rather than placeholder text. Press Return to accept it immediately, or simply type to replace the whole selected prompt.

## 5.4.4 — Signal Camera + Service-Safe Media

Signal can now attach a rear-camera photo directly from an iPhone/browser with the **CAM** control beside the chat input. The capture is a normal image attachment, not a special command: take a photo, type `what am I looking at?`, and LO follows the existing vision-capability path. Signal materializes the image at the browser edge; LO/Fabric then stages image bytes as an artifact before inference, so large camera payloads do not ride inside Fabric work packets.

Media playback from Signal is also hardened for service environments. LOOK now finds mpv in common Linuxbrew/Homebrew/system locations even when the Signal service lacks an interactive-shell PATH, and failed media tools return the playback edge diagnostic instead of collapsing everything to `MEDIA PLAY FAILED`.

The existing 5.4.3 shared MediaSession card remains unchanged: browser, terminal LO, and `lk media` all control the same canonical playback session.

## 5.4.3 — Signal Media Card

Signal can now render the canonical LOOK MediaSession as a compact live browser control surface. Start playback from LO, the terminal, or Signal itself and the card appears automatically with now-playing metadata, progress, previous/play-pause/next, stop, queue count, an expandable queue, and direct queue-item jumps. Closing or dismissing the card never owns or terminates playback; it is another renderer over the same LOOK/mpv session.

```bash
lo play talking heads
# Open Signal: the shared player card appears automatically.
```

Signal 1.3.0 also exposes `/player` to rediscover a dismissed active session. The browser polls lightweight media state and sends deterministic transport commands back through LOOK; no second browser-specific playback engine exists.

## 5.4.2 — Island Resilience + Workstation Editor

LOOK is explicitly a complete one-node system: remote Fabric adds capability but is never required for deterministic tools, local files, local memory, media, or local inference. `lk doctor island` performs a loopback-only autonomy audit and reports the local capability ladder without consulting Tailscale or remote nodes.

Future Crash Workstation and Ask now render editing from one authoritative text buffer plus logical cursor index. Backspace, insertion, left/right movement, long-line viewport scrolling, and terminal redraw no longer depend on stale screen columns. The Workstation help documents the editing keys.

Documentation, `lk help`, the canonical command registry, Zsh completion, man page, release history, and installer/version surfaces are synchronized with this release.

## 5.4.1 — Playback Ownership + Controller Repair

LOOK probes/reuses its existing mpv worker before touching the IPC socket, reaps only LOOK-owned orphan players, and makes stop/queue-clear terminate all LOOK playback workers. Explicit next-album language remains deterministic. The installer also normalizes the OpenJev-aware Local Labs `server` controller.

## 5.3.0 — Decision Plane

5.3.0 makes uncertainty a first-class Fabric object. A job can ask the human a tiny question without making a terminal or browser a lock: DecisionRequests carry choices, confidence, consequence, reversibility, a deadline, and an explicit timeout policy. Power/Unsafe may continue low-consequence reversible work after silence; Workspace/Conservative defer; destructive or irreversible work still requires explicit confirmation.

Decision requests are renderer-neutral and visible across trusted Fabric nodes. `lk fabric decisions` lists pending requests, `lk fabric answer ...` resolves one, and Signal can surface the same request with one-tap choices. The answering UI does not execute work; any continuation is still a normal authorized Fabric Work Packet.

OpenJev is an optional first-class Fabric decision worker, configured canonically at `http://127.0.0.1:8791` when installed. The Decision Plane remains authoritative: deterministic fast paths stay instant, learned judgment supplies bounded evidence, and missing/broken OpenJev degrades cleanly to existing behavior. `lk fabric decision-provider` shows worker state; `lk fabric decision-shadow ...` remains available for direct probes.

## 5.2.19 — Media Session Reliability

Media becomes a first-class Fabric capability rather than a phrase LO can mistake for web search. LO now exposes deterministic `media_search`, `media_play`, `media_queue`, and `media_control` tools, and narrow local commands such as `lo play Talking Heads` are routed to the Fabric media catalog before inference. Explicit online requests still use the web path.

`lk media find` now uses LOOK filter semantics: type to refine immediately, Tab to multi-select, and uppercase contextual actions (`P` play, `Q` queue, `A` queue visible matches, `I` info, `S` save selection, `C` clear). Display labels remain presentation only; actions operate on exact catalog rows/artifact identity.

## 5.2.17 — Fabric Media Catalog + LOOK Selector

Media remains a reference workload, not a product direction. `lk media find` and `lk media browse` now use a LOOK-native selector so display names never have to be retyped exactly; Enter plays the selected item, Space queues it, and filtering stays inside the selector. Fabric also publishes the union of media scanned on currently online nodes, with SHA-identified copies collapsed by content identity and shell completion drawing from the same catalog.

```bash
lk media fabric
lk media browse
lk media find "talking heads"
lk media identify --all        # local node: promote discoveries to SHA identity
lk media play tal<Tab>
```

A scan remains cheap metadata discovery. SHA-256 identity is progressive: explicit registration, streaming, or `identify` promotes a discovered path into the generic Fabric artifact catalog without making every scan an expensive hashing pass.

---


## 5.2.16 — Media Sessions + Library Queue

Fabric's streaming-artifact proof now has a deliberately small daily-use media surface. `lk media scan ROOT` builds a fast dependency-free catalog, `lk media play` can construct queues from files/directories/albums/artists/search text, saved playlists persist the queue independently of the playback engine, and `lk player` provides a tiny live terminal miniplayer. mpv still owns decoding/rendering; LOOK owns queue/session meaning. No media root is hard-coded.

```bash
lk media scan /srv/media/music
lk media play "Remain in Light"
lk media queue
lk player
lk media save Driving
```

---


## 5.2.1 — Evidence labels

Native interfaces now carry LOOK provenance with the answer. Canonical tool/search receipts remain sourced; an answer with no receipt is labeled `MODEL · INFERRED`. Future Crash Ask also returns to a normal conversational flow: after an answer, simply type the next question.


**Personas + Fabric Memory**

5.2 makes the architecture explicit: **persona is presentation; Fabric is intelligence**. Future Crash Ask and X Workstation both speak as Oracle through the same LO/Fabric engine, with trusted time, tools, user access profile, scoped memory, and conductor routing. Oracle can land on the M4, M3, or 3090 without changing identity.

New memory commands:

```bash
lk memory fabric
lk memory shared
lk memory persona oracle
lk memory add-shared "..."
lk memory add-persona oracle "..."
lk memory add-local "..."
lk memory sync
```

Fabric Memory is intentionally small and inspectable. Shared and persona scopes replicate across live trusted nodes; node scope stays local. Existing LO memory and Future Crash local memory are preserved.

---

# Future Crash + LOOK 5.1.6 — Conversation Channels


## 5.1.6: Future Crash conversation channels

Future Crash keeps three outputs separate: conversational text, Signal visuals, and telemetry. Oracle/Workstation answers are committed to the normal transcript first. If a visual was requested, a dedicated Signal compiler receives the operator request plus the finished answer and updates the canvas as a sidecar. Signal receipts are compiler feedback/status only; they are not conversation messages.

This also keeps the large Signal grammar out of ordinary short prompts, which makes small models less likely to answer a greeting with render protocol instead of prose.

The Fabric dashboard now says what its HTTP counters actually mean. `conn` counts accepted TCP sockets, `req` counts successfully parsed HTTP requests, and `done` counts request handlers that reached a terminal state. This matters for the guarded Tailscale ingress because health probes, abandoned sockets, or incomplete HTTP handshakes can legitimately make connections much larger than requests without implying a leak.

The dashboard also gains **`f` to freeze**. Freezing stops dashboard polling/repaint only; Fabric services, inference, Signal, and peer traffic continue normally. Press `f` again to resume.

Example control-plane line:

```text
local   conn 1820   req 1820   done 1820   active 0   rej 0   err 0   rate 0.32/s
ingress conn 361    req 123    done 123    active 0   rej 0   err 0   no-http 238  early 0  rate 0.08/s
```

The second line is no longer mysterious: 238 accepted ingress connections did not become valid HTTP requests. That is now visible as its own state rather than being mistaken for unfinished work.


This is the last weather-specific correctness pass. WEATHER now behaves like a typed Fabric capability rather than conversational prose: location-changing follow-ups stay attached to the active weather place, daily high/low values come directly from canonical receipt fields, and an accuracy challenge can trigger an independent National Weather Service observation check. The point is not to grow a weather app; it is to finish the receipt/follow-up pattern so the same machinery can move on to web, filesystem, calendar, services, and other capabilities.

Regression conversation:

```text
weather in portland
how about beaverton or
what is the high and low today
is that accurate?
```

The third turn must read Beaverton's typed daily extrema. The fourth may compare Open-Meteo against the nearest available NWS observation without silently choosing one provider as truth.

A milestone release: the personal Fabric is observable, routable, pulse-synchronized, and now has a tiny physical-looking demo of itself. Deterministic Fast Edges keep obvious tool work out of unnecessary model-planning rounds, while LO adds a restrained patient waiting cadence for genuinely long inference.

## Show somebody the Fabric

Open the dashboard on every node:

```sh
lk dash
```

Then press **`b`** in any dashboard, or run:

```sh
lk fabric beacon
```

Every open dashboard schedules the same RGB flash against a future shared Fabric pulse. The packets may arrive at different moments; presentation is synchronized by the pulse. The command prints delivery receipts for each node. This is deliberately inference-free: if it works, peer discovery, event transport, the control plane, and shared pulse timing are all alive.

For a quieter test:

```sh
lk fabric beacon pulse
```

## 5.0 optimization: Fast Edge really means fast

For deterministic weather questions, LO retrieves the canonical live receipt first and then gives the reflex model only the trusted temporal context, weather receipt, and user question. It no longer makes a small model reread the full LO tool/context manual simply to phrase data we already have.

**Signal Native LO.** Signal no longer spawns the human `lo` terminal command or parses terminal output. The browser calls a reusable in-process LO engine, receives structured events/results, keeps a bounded session history for follow-ups, and presents artifacts in the originating browser. The Fabric remains the inference substrate underneath LO.

# Future Crash + LOOK 4.5.0 — Fabric Packets

The Fabric now has a durable work protocol: immutable `fwp/1` packets, a local job ledger, attempts/results/events, capability and authority contracts, content-addressed artifacts, remote packet forwarding, cancellation, and a live multi-node event tape. See `docs/FABRIC-WORK-PACKET.md`.

# FUTURE CRASH + LOOK 4.2.0 — FABRIC CONTROL

**One install. Every machine is a node. LOOK, LO, Future Crash and Signal are interfaces onto the same small local-first system.**

See `docs/UNIFIED-NODE-4.0.md`.

4.2 adds a capability-scoped control plane and live Fabric monitor. From any node you can inspect another node, qualify one of its models, inspect managed services, or explicitly confirm a bounded service action. `lk fabric watch` provides the live operating view. Fabric does not expose arbitrary remote shell execution.

```text
lk fabric watch
lk fabric models 3090
lk fabric qualify 3090 qwen3.8:27b
lk fabric services 3090
lk fabric service 3090 signal restart
```

---

# FUTURE CRASH + LOOK

**A local-first AI terminal environment for macOS and Linux.**

![Future Crash terminal](FC_screenshots/Normal.png)

Future Crash is the place you inhabit. **LOOK is the machinery underneath it.**

Future Crash gives a local language model a playful terminal front end. LOOK gives the terminal underneath it a compact language for navigation, files, machine inspection, Ollama, remote models, memory, learned skills, and controlled agentic work.

They started as separate projects. They now install and live as one system.

---





## LOOK 2.0: your LOOK is portable

LOOK now treats your evolving local AI as a first-class **profile**, separate from the software package and from disposable machine/runtime state.

```text
lk profile
lk profile backup ~/Documents/LOOK
lk profile export
lk profile restore look-profile-....zip
```

Memory, recent continuity, core customization, learned skills, personalities, behavioral preferences, and feedback settings travel. Secrets, undo/trash, jobs/events, worker queues, PIDs, caches, and machine-specific host plumbing do not.

For presentation preferences:

```text
lk feedback
lk sound
```

Sound is off by default; motion is subtle by default. Both degrade to nothing for piped output.


## Filer → LO context

LOOK's filer can hand its current working set directly to LO.

1. Filter/select files normally.
2. Mark any number with `Tab` or `A` (or leave one highlighted).
3. Press **`L`**.

LO opens immediately with those paths named as the selected context:

```text
context · 6 selected paths
you ›
```

The files are **not** blindly stuffed into the model context. LO receives their paths and uses its normal bounded `read_file`, `list_files`, `search_files`, and mutation tools only when the request requires them. The LO workspace is rooted at the nearest common selected directory, so the handed-off paths are actually accessible to the session.


## LO execution receipts

LO distinguishes **planning** from **execution**. For explicit filesystem changes, LOOK will not accept a prose-only success claim: an actual mutation tool must run first. Several new text files should use the bounded batch creator; routine process/port diagnosis uses read-only host inspection tools even in Workspace mode.

Workspace remains bounded: it can inspect the host and mutate files inside the starting workspace, but arbitrary shell commands still require Power or Unsafe mode.


## LO continuity

LO keeps three deliberately different memory layers:

- **Recent conversation:** a small literal cross-session ring. This is what lets a fresh `lo` session understand “what happened to those files?” from a recent exchange.
- **Candidate memory:** semantic facts/project state with importance scores. Unreinforced candidates decay; zero means forgotten.
- **Long-term:** a compact background summary periodically consolidated from candidates that remain strong or are reinforced.

`lk memory` shows all three states. `lk memory clear-recent` clears only recent literal conversation.

For filesystem work, LO can create several new text files in one bounded operation rather than spending one model/tool round per file. Direct shell helpers also accept batches:

```text
lcp a.txt b.txt archive/
lmv one.md two.md notes/
lrm old1.txt old2.txt
```

Copy/move batches use the existing LOOK undo transaction machinery.


## Starter toolkit

You can use all of LOOK while remembering only a few entrances:

```text
lk system    machine health, processes, ports
lk ai        models, benchmark, thinking, personality
lk net       addresses, Tailscale, sharing, web readiness
lk clean     conservative maintenance
lk config    LOOK and LO behavior

lo           talk to LO
fcr          Future Crash
```

These are keyboard-driven control surfaces over the existing commands, not replacements. Experienced users can still go directly to `lk doctor`, `lk models`, `lk thinking deep`, `lk tailscale`, and the rest.

Use `lk commands` for the terse vocabulary index and `lk help all` for the complete command/key glossary.


## Install

Installation happens in Terminal, but it is intentionally simple.

### 1. Download and unzip the release

Open Terminal. Type `cd ` — including the space — then drag the unzipped `future-crash-look-1.3.0` folder into the Terminal window and press Return.

Or navigate there normally:

```sh
cd ~/Downloads/future-crash-look-1.3.0
```

### 2. Give the installer permission to run

```sh
chmod +x install.sh
```

`chmod +x` simply marks the installer as executable. You normally do this once for a downloaded release.

### 3. Run it

```sh
./install.sh
```

The installer sets up Future Crash + LOOK, the shell integration, LOOK's command-line tools, documentation, and the optional terminal experience. It may also offer supporting software such as Tailscale or Ollama when they are not already present.

When it finishes:

```sh
exec zsh
future-crash
```

That is the front door.

![Future Crash after install](FC_screenshots/Normal.png)

The installer is rerunnable. A newer release updates the files the project owns; the same release reconciles them. Version-aware installers refuse to overwrite a newer release unless you deliberately use `--force-downgrade`.

---

## The idea in thirty seconds

There are three pieces:

```text
Future Crash   the experience
      ↓
LOOK           the terminal language and tools
      ↓
LO             the working local/remote AI
      ↓
Unix + Ollama  ordinary files, processes, models, network
```

You can live almost entirely in Future Crash, drop into LOOK when you want the underlying machine, or use LO directly when you want the AI without the Future Crash front end.

![Future Crash interface](FC_screenshots/Normal_3.png)

### Future Crash

Launch it with:

```sh
future-crash
```

or the shorter aliases:

```sh
fcr
rst
```

Future Crash is conversational and ambient: observations, fortunes, system context, AI conversation, and the sense that the terminal itself has a personality.

Press `Esc` to expose the shell underneath. Type:

```sh
exit
```

to return to the same Future Crash session.

Nested Future Crash sessions are blocked by default so you do not accidentally end up six shells deep.

![Future Crash view](FC_screenshots/Error_2.png)

### LO information edges

LO has a deliberately small set of canonical read-only sources before generic web search:

- `weather` — live current conditions and short forecast via Open-Meteo; no key required.
- `place_lookup` — place-name/postal-code resolution to coordinates and timezone via Open-Meteo.
- `wikipedia` — compact English Wikipedia article search for stable encyclopedic background.
- `web_search` — Ollama-hosted generic search for current/open-ended material when `OLLAMA_API_KEY` is configured.

The model chooses the appropriate edge. Retrieval is visible in the terminal (`weather ›`, `place ›`, `wiki ›`, `search ›`) and the returned data is compact so it does not flood the local model's context.

## LOOK

LOOK is the practical layer underneath Future Crash:

```sh
lk
```

It handles navigation, fuzzy finding, filtering, file inspection, system information, Ollama hosts and models, settings, memory, skills, and other small pieces of the machine.

A few useful starting points:

```sh
l
lr
lz
f
lk machine
lk doctor
lk settings
```

![LOOK file filter](FC_screenshots/LOOK_Shell_filter_find.png)

### LO

LO is LOOK's direct AI interface:

```sh
lo
```

It is conversation-first. File tools are available, but LO does not search the workspace merely because a tool exists. Casual conversation stays conversation; file and system tools come into play when the request actually calls for them.

```sh
lo
lo search
lo --conservative
lo --workspace
lo --power
lo --unsafe
```

![LOOK AI](FC_screenshots/LOOK_AI.png)

Future Crash and LO share the same selected Ollama model and host.

---

## First five minutes

After installation:

```sh
future-crash
```

Explore it for a moment. Press `Esc` to reveal the shell, then try:

```sh
lk
l
lk machine
lo
```

Inside LO, ask something conversational. Then ask it to inspect a file in the current folder. The point is that the same interface can move from ordinary conversation to real local work without pretending those are the same permission.

If you want to see what LO remembers:

```sh
lk memory
```

If you want to see what LO has learned about *doing its job*:

```sh
lk skills
```

![Future Crash / LOOK transition](FC_screenshots/Normal_2.png)

---

## AI setup

Future Crash + LOOK does not bundle a language model. It works with **Ollama**.

### Local model

If Ollama is installed on the same machine, pull any model appropriate for the hardware. For example:

```sh
ollama pull qwen3:8b
```

Then inspect or select models with:

```sh
lk ollama models
```

A lighter machine can use a smaller model. A workstation with more memory can use a much larger one.

### Remote model

The interface and the model do not have to run on the same computer.

A laptop can run Future Crash + LOOK while a desktop workstation runs Ollama:

```text
MacBook / Linux laptop
  ├── Future Crash
  └── LOOK / LO
         │
      Tailscale
         │
GPU workstation
  └── Ollama
```

Manage saved hosts with:

```sh
lk ollama host
```

Once a host is selected, Future Crash and LO inherit it automatically.

![Future Crash machine context](FC_screenshots/PNC.png)

### Web search

Ollama web search uses an Ollama API key. Configure it once:

```sh
lk ollama key
```

Check the configuration without exposing the key:

```sh
lk ollama key status
```

Web search is optional. LOOK's normal terminal features do not depend on it.

---

## Permission levels

LO separates **intelligence** from **permission**.

| Profile | What LO can do |
| --- | --- |
| **Conservative** | Read/search and reason; no writes |
| **Workspace** | Read and intentionally edit inside the starting workspace |
| **Power** | Workspace tools plus shell commands, confirmed individually |
| **Unsafe** | Unrestricted shell commands with the current user's privileges |

Workspace is the normal working mode. Unsafe is intentionally named.

Change the persistent profile from:

```sh
lk settings
```

or choose a one-session override:

```sh
lo --conservative
lo --workspace
lo --power
lo --unsafe
```

---

## Memory: small, selective, forgetful

LO does not dump a giant transcript into every prompt.

Its live working context is explicitly bounded at 8192 tokens. Core system/workspace context stays fixed while recent conversation is retained under both a message-count and serialized-size budget; older continuity is expected to survive through memory rather than an endlessly growing transcript.

It also keeps a bounded pool of candidate memories and only exposes a small working set to the model. Candidate memories have importance values, decay when they stop mattering, and strengthen when they genuinely prove useful.

```sh
lk memory
```

The design is deliberately simple:

```text
conversation
   ↓
candidate memories
   ↓
decay / reinforcement
   ↓
small working context
   ↓
durable patterns
   ↓
long-term summary
```

Explicit requests such as “remember this long term” can promote information directly into the long-term summary. The summary is not sacred or append-only; it periodically rewrites itself under a fixed size budget so stale, redundant, superseded, or low-value details can disappear.

Memory is stored in human-readable JSON and carries a **schema version**, so future LOOK releases can migrate the data format without treating the contents of your memory as an application version.

![LOOK doctor](FC_screenshots/LOOK_Shell_doctor.png)

---

## Skills: LO's accumulated craft

Memory is about **you**. Skills are about **how LO works**.

LO ships with reviewed bundled skills such as:

- inspect before modifying;
- prefer surgical changes over rewrites;
- preserve unrelated behavior;
- test changes when practical;
- treat user-owned shell configuration conservatively.

LO can also learn generalized techniques from successful work and place them in the `## Learned` section of `skills.md`.

```sh
lk skills
```

You can inspect and edit the file directly, or use:

```sh
lk skills add "Inspect the existing configuration before changing it"
lk skills forget "configuration"
lk skills clear-learned
```

### Skills have their own version

The application and the craft pack are intentionally separate concepts:

```text
Future Crash + LOOK   application release
memory schema         data-format version
skills schema         skills-file format
bundled skills pack   reviewed craft version
```

Check the installed craft pack:

```sh
lk skills version
```

Update the bundled section from the current release while preserving everything LO learned locally:

```sh
lk skills update
```

You can also merge another compatible skills pack:

```sh
lk skills update /path/to/skills.md
```

That means the program can eventually stabilize while the reviewed assistant craft continues to improve independently.

---


## Signal Field as an expressive channel

### Signal wiring fix

Future Crash preserves valid `[[SIGNAL]]` blocks even when an Ollama/Qwen model places them in structured thinking. Reasoning prose remains hidden; the Signal directives still reach the renderer. Workstation and Oracle views also restore a larger roughly half-screen Signal pane on ordinary desktop widths, and the built-in Dream thread has a visual fallback so every successful wake produces visible Signal activity.


Future Crash can now treat Signal as part of its native language rather than a special-case drawing trick.

- Ask and Workstation may use Signal when a visual genuinely improves the answer.
- Signal is explicitly modeled as a **40×12 addressable character framebuffer**. It can work at three levels: semantic primitives (`PLOT`, `BARS`, circles/arrows), vector geometry (`LINE`, `BOX`, `TEXT`), or exact raster composition (`SPRITE`, `PUT`).
- `SPRITE x y color ... END` preserves character-art whitespace; spaces are transparent, so sprites can layer over other Signal content.
- `BARS x baseline_y color ...` turns normalized values into deterministic host-rasterized columns for EQs, meters, spectra, and dashboards.
- Signal renders produce a tiny persistent receipt with modes used, accepted/rejected commands, clipping, nonempty cells, occupied dimensions/bounds, title, and frame count.
- The latest few receipts are fed back to Future Crash so later drawings can improve.
- Signal supports tiny multi-frame animations with `FPS` + `FRAME`.
- The Threads screen has a built-in **Signal Dream** preset: press `D` to toggle a roughly four-minute model-only dream thread.

Signal history is intentionally tiny and bounded. It is craft feedback, not a screenshot archive.

Future Crash memory is still lean, but its recent conversational buffer now keeps eight completed Workstation exchanges before consolidation rather than five, and the long-memory budget is modestly larger. The principle remains the same: keep enough continuity to be useful, then compress.


## Future Crash personality boundary

Future Crash and LO share the same Ollama substrate, but they do **not** share personality selection.

Future Crash owns a fixed application personality in:

```text
~/.local/share/future-crash/personality.md
```

LO remains user-selectable (`lo`, `robot`, `max`, `philosopher`). Switching LO personality therefore does not turn Future Crash into Philosopher or Space Robot.

Short Future Crash artifacts—fortunes, ambient/oracle observations, and similar micro-generations—are **final-only**. Future Crash reserves a fixed three-line Fortune body beneath its `FORTUNE //` label, keeping the ambient layout stable as fortunes wrap. If a model returns only prompt-paraphrase/reasoning instead of a final artifact, Future Crash now fails closed to the local Future Crash seed rather than displaying model internals. Model reasoning is discarded before the text reaches the interface, including Qwen/Ollama template cases where a stray closing `</think>` appears in visible content.

---

## LO personality and thinking

LO now has three independent controls. They deliberately do different jobs:

```text
CAPABILITY    what LO is allowed to do
PERSONALITY   how LO speaks and approaches the interaction
THINKING      how much deliberation and how that work is presented
```

Choose them interactively with `lk settings`, or directly:

```sh
lk personality lo
lk personality robot
lk personality max
lk personality philosopher

lk thinking light
lk thinking adaptive
lk thinking deep

lk think-display compact
lk think-display full
lk think-display quiet
```

The four bundled personalities are ordinary Markdown instruction packs:

- **LO** — balanced, concise, curious, practical.
- **Space Robot** (`robot`) — dry, strange, retro-futurist, gently nonhuman.
- **Max** — rapid, punchy, synthetic-TV energy without sacrificing technical clarity.
- **Philosopher** — first-principles, reflective, with restrained poetic language.

They live in `~/.local/share/look/personalities/`. The active selection is separate from the files, so personality packs can be replaced or updated independently of user memory, skills, model choice, and capability level.

### Rolling thinking

`compact` is the default thinking display. Rather than dumping a large reasoning block after the wait, LOOK consumes Ollama's streaming response and promotes readable chunks into a small live rolling view. The goal is to show that work is progressing without turning every answer into a wall of process text.

`full` exposes the visible thinking stream as readable chunks. `quiet` minimizes reasoning display. These are presentation choices; they do not change capability permissions.

Thinking depth defaults to `adaptive`. On models that advertise Ollama thinking support, these are real runtime controls rather than prompt-only hints: `light` disables deliberate thinking with an 800-token output ceiling, `deep` enables it with 2000 tokens, and `adaptive` uses a 1400-token ceiling while enabling thinking only for clearly analytical, debugging, coding, or multi-step requests. All modes use an 8192-token working context.

The ceilings are intentionally generous and are not targets: a short answer still stops early. Background memory/skill maintenance is separate and uses much smaller no-thinking budgets.

---

## Smart make

`lmk` — **LOOK make** — collapses the two ordinary Unix creation primitives into one predictable command.

```sh
lmk notes.txt       # create an empty file
lmk project/        # create a directory and enter it
lmk src/utils.py    # create a file inside src/
lmk projects/demo/  # create the directory path and enter demo/
```

LOOK uses obvious syntax first:

- a trailing `/` means **directory**;
- a filename suffix such as `.md`, `.py`, or `.txt` means **file**;
- dotfiles such as `.gitignore` are treated as files;
- an extensionless name is genuinely ambiguous, so LOOK asks:

```text
LOOK make · project is ambiguous
[d] directory + enter · [f] file · Esc cancel ›
```

The choice is immediate: press `d` or `f`; no Return is required.

```text
```

For scripts or muscle memory, force the choice:

```sh
lmk -d project      # directory + enter
lmk -f Makefile     # file
```

If a file path needs parent directories that do not exist, LOOK asks before creating them.

Both files and directories are journaled through LOOK:

```sh
lk undo
```

A newly created empty file can be removed by undo while it is still unchanged. A newly created directory can be undone while it remains empty. LOOK refuses destructive undo once either object has acquired meaningful contents.

The older `mkd DIR` helper remains as a compatibility shortcut for `lmk -d DIR`, so it now uses the same journal and undo behavior.

---

## Media controls

LOOK also exposes a tiny transport layer for music that is already playing:

```sh
lk media
lk media toggle
lk media next
lk media prev
lk media stop

Fast shell aliases:

```sh
mm    # play / pause
mn    # next track
mp    # previous track
```
```

On macOS, LOOK currently controls running **Music** or **Spotify** through their system scripting interfaces. On Linux it uses the standard **MPRIS** ecosystem through `playerctl`.

`lk media` reports the active supported player, state, and track where available. Every successful transport command also reports the resulting state immediately, so `mn` both skips and confirms what is now playing. The public interface stays the same even though the platform adapters underneath are different.

---

## Command completion

LOOK teaches Zsh its grammar.

Try:

```text
lk <Tab>
lk ollama <Tab>
lk ollama host <Tab>
lk memory <Tab>
lk skills <Tab>
lk media <Tab>
lmk <Tab>
```

Saved Ollama host names are completed dynamically.

LO completes only its structural options and host selectors. After that, the command line is natural-language input rather than a giant command tree.

---

## The command map

You do not need to memorize this. Start with `future-crash`, `lk`, and `lo`.

| Command | Purpose |
| --- | --- |
| `future-crash` / `fcr` / `rst` | Launch Future Crash |
| `lk` | LOOK command center |
| `lo` | Direct AI conversation |
| `l` | LOOK around / navigate |
| `lr` | Recent ordering |
| `lz` | Size-oriented view |
| `f` | Find under home |
| `lmk` | Smart make: file or directory |
| `lk machine` | Machine/system view |
| `lk doctor` | Diagnose the environment |
| `lk settings [SEARCH]` | Search-first settings control room |
| `lk ollama models` | Inspect/select models |
| `lk ollama host` | Inspect/select hosts |
| `lk ollama key` | Configure web-search key |
| `lk memory` | Inspect user memory |
| `lk skills` | Inspect assistant craft |
| `lk skills version` | Show skills schema/pack version |
| `lk skills update` | Refresh Bundled craft, preserve Learned |
| `lk media` | Show media state |
| `lk media toggle` | Play/pause |
| `lk media next` / `prev` | Next/previous track |

Long informational displays such as `lk skills` and `lk memory` use LOOK's pager when appropriate, so they remain readable as they grow.

For the complete LOOK vocabulary:

```sh
lk help
man lk
```

---

## The terminal experience

Future Crash + LOOK runs in an ordinary Zsh terminal.

The reference visual stack is:

| macOS | Linux |
| --- | --- |
| iTerm2 | Kitty |
| Zsh | Zsh |
| Powerlevel10k | Powerlevel10k |
| MesloLGS NF | MesloLGS NF |

The installer can offer/check the pieces it can safely manage. Declining them does not disable the core project.

> **Portable by default. Gorgeous when equipped.**

![LOOK home](FC_screenshots/LOOK_home.png)

---

## Interactive typing

LO's `you ›` prompt uses readline/libedit when available, so normal terminal editing works:

- Left / Right arrows move within the line.
- Up / Down arrows recall input history.
- Home / End work where supported.
- Backspace/delete behave normally.

At the Zsh prompt, `lo` is a `noglob` alias, so characters such as `?`, `*`, and brackets can be used in one-shot prompts without turning into filename globs:

```sh
lo Do you know the band The Police?
```

Unmatched shell quotes are still parsed by Zsh before LO can see them. For unrestricted prose, simply enter interactive LO first:

```sh
lo
```

---

## Where it lives

The project uses ordinary Unix-style locations:

```text
~/.local/share/look/                  LOOK code + state
~/.local/share/future-crash/          Future Crash
~/.local/bin/lk                       LOOK launcher
~/.local/bin/future-crash             Future Crash launcher
~/.config/look/look.zsh               managed shell vocabulary
~/.config/look/completions/           Zsh completion definitions
~/.zsh_secrets                        user secrets
```

Your `~/.zshrc` remains your file. The installer backs it up and adds a small marked source hook rather than replacing it.

---

## Updating and version safety

This release establishes the following baseline:

| Layer | Version |
| --- | ---: |
| Future Crash + LOOK | **2.3.4** |
| LOOK | **4.3.4** |
| Future Crash | **1.1.15** |

Signal rendering is now compiled separately from conversation: explicit Signal requests use a focused no-thinking 1200-token render pass, while ordinary Workstation conversation retains its own reasoning budget.
| Memory schema | **1** |
| Skills schema | **1** |
| Bundled skills pack | **1** |

To update from a newer release directory:

```sh
./install.sh
```

The installer records product/component versions in:

```text
~/.local/share/look/install_manifest.json
```

A version-aware installer refuses to overwrite a newer unified release. A deliberate rollback remains possible:

```sh
./install.sh --force-downgrade
```

Historical installers that predate this guard cannot be made version-aware retroactively.

---

## Uninstall

From a release directory:

```sh
./install.sh --uninstall
```

or from an installed system:

```sh
lk uninstall
```

The uninstall removes files the project knows it owns. It does not casually remove unrelated Homebrew packages, Ollama, Tailscale, models, personal memory, or secrets.

![Future Crash interface](FC_screenshots/Error.png)

---

## Why Future Crash + LOOK are one project

Separate installers eventually became artificial.

Future Crash depended on the same model selection, remote-host logic, terminal behavior, memory, and shell environment that LOOK already managed. The unified project keeps the modules separate internally while treating distribution honestly:

```text
Future Crash   experience / personality
LOOK           terminal language / machine tools
LO             AI conversation / agency
Ollama         local or remote inference
Unix           files, processes, shell, network
```

One repository. One installer. One shell integration. One AI configuration.

The code remains modular because **one product does not require one giant program**.

---

## Design principles

**Local first.** Files and state remain ordinary local computing primitives.

**Keyboard first.** Fast paths should become muscle memory.

**Boring underneath.** Files are files. Commands are commands. Configuration has visible locations.

**Progressive power.** Reading a file and running an unrestricted shell command are not the same permission.

**Small memory.** Remember more than you think about at once; forget what stops mattering.

**Accumulated craft.** The model supplies raw intelligence. LOOK supplies learned technique.

**Remote without becoming cloud software.** A laptop can use your own workstation over a private network.

**Readable machinery.** The project is Python, shell, Markdown, and JSON—not an opaque application bundle.

---

## Platform and status

Future Crash + LOOK is designed around **macOS and Linux**, Zsh, Python 3, and ordinary Unix tools.

LOOK itself is lightweight. Local-AI hardware requirements are mostly determined by the model you choose. Remote Ollama support exists precisely so the machine running the interface does not have to be the machine doing the inference.

This remains an enthusiast-built terminal environment with intentionally powerful modes. Keep normal backups and understand Power/Unsafe before enabling them.

The point is not to make the terminal disappear.

**The point is to see what the terminal becomes when it can think.**

### Filer navigation note

Filer navigation is deliberately vertical: `j/k` (or `J/K`) and ↑/↓ move through matches. `L` is reserved for handing the current highlighted/marked set to LO as context.


### Filer parent navigation

In ordinary browse mode, press `<` (Shift-,) to move up one real filesystem directory. Escape remains navigation-history back. While typing a filter, `<` stays ordinary filter text.


## Persistent filer working set

Selections now survive navigation. Mark files or directories with `Tab`/`A`, move through the filesystem with Enter and `<`, and keep collecting paths from other locations.

```text
SELECTED · 3
SELECTED · 7 / 3 HERE
```

The first form is green and means the selected set is local to the current view. The second uses an amber accent and means the working set spans locations; seven paths are selected in total and three are here.

`C` copy, `M` move, `R` remove, `Y` paths, clipboard actions, and `L` LO context use the accumulated working set. `X` clears it. Selecting a directory records the directory path; it does not recursively mark every descendant.


### Filter navigation

While actively typing a filter, lowercase `j` and `k` remain filter text. Navigate matches with `J/K` (Shift-J/Shift-K) or ↑/↓. Outside filter entry, ordinary `j/k` navigation remains available.


## Path completion

Filesystem destination fields are path-aware. In filer copy/move prompts:

```text
COPY 3 items · to › ~/Down<Tab>
                         ↓
                     ~/Downloads/
```

The same rule applies to shell helpers such as `lcp`, `lmv`, `lrm`, and `lscp`: every operand is a filesystem path and may be completed repeatedly with Tab.

## LOOK-native global find

`f` keeps its broad `$HOME` search scope but now uses LOOK's own filter, preview, selection, working-set, and action language instead of dropping into a stock fzf screen. `fd` remains the preferred fast catalog source when installed.

`fznv` uses the same LOOK-native finder and opens the chosen file in Neovim.

## Temporal LO memory

LO now receives explicit age information for recent exchanges and semantic memories. Candidate memories carry creation and last-reinforcement timestamps.

The governing rule is:

> Memory describes what happened. It is not a pending instruction queue.

An older unfinished request may provide context, but LO must not silently resume it unless the current request clearly asks to continue.

## Background LO jobs and events

LOOK now has a small durable message-passing layer:

```text
shell / filer / Future Crash
        ↓
      jobs/
        ↓
       LO
        ↓
      events/
        ↓
 next shell prompt
```

Queue work with:

```text
lo bg summarize these logs and tell me what failed
```

Continue using the terminal normally. When the job completes, LOOK emits a completion/failure event that is surfaced at the next shell prompt.

Inspect state with:

```text
lk jobs
lk events
```

This is intentionally not a resident daemon yet. The filesystem queue/event contract establishes the interface first; a future Unix-socket or localhost service can implement the same contract without changing callers.


### Batch transaction safety

Multi-file copy/move is one transaction even when the undo history is already full. LOOK tags each temporary mutation with a transaction ID, then commits one batch undo record. On failure, only that transaction is rolled back and the receipt identifies the source that failed.

Interactive file-action prompts use Tab for completion and bare Escape for clean cancellation.


### Streaming global find

`f` and `fznv` intentionally use a streaming picker for the global `$HOME` search. You can begin typing immediately while `fd`/`find` continues producing candidates. The picker uses LOOK-style colors and indicators; `f` then hands the selected result into LOOK for normal actions.



## Living with LOOK

For a non-reference explanation of how Future Crash, LOOK, LO, files, background work, and canonical information sources fit into an ordinary workflow, see `docs/LIVING-WITH-LOOK.md`. Information provenance is documented in `docs/INFORMATION-EDGES.md`.

### Adaptive LO headroom

LO now selects a FAST, STANDARD, or DEEP runtime budget instead of forcing every request through the same 8k context and short generation ceiling. Standard tasks get 16k context / 3.5k output / 8 tool rounds; deep tasks get 24k / 6k / 12.

These values are maximums, not targets. Inspect classification with:

```text
lk budget count only the files in this directory tree
```

This makes model benchmarking fairer: compare 4B/8B/30B against the same adequately provisioned LO runtime rather than against an artificially cramped agent.

### Deterministic directory inspection

LO has a dedicated read-only directory inspector for exact file/folder counts and size statistics. It should use that instead of asking the model to count a long listing.

### Learning from feedback

Natural feedback can act as weak supervision. Clear praise or criticism queues a quiet background review of the previous interaction. Reusable lessons may be added, reinforced, weakened, or corrected; ambiguous feedback does nothing.

```text
lk skills state
```

shows the reinforcement state. `skills.md` stays human-readable while `skill_state.json` carries confidence metadata and is included in the portable profile.


## Living AI (2.1)

LOOK runs a tiny resident local broker (`look_ai.py`) that coordinates explicit background jobs, memory maintenance, and skill reflection against the configured local/remote Ollama service. Interactive LO work establishes foreground priority; background cognition happens while you are doing something else.

`lk ai` shows the live queue/broker state. Memory consolidation is now semantic, time-aware, and event-driven rather than tied to conversation count.


## Shared inference coordination

LOOK 2.1.2 keeps LO and Future Crash as separate minds while coordinating the inference resource underneath them.

- LO/LOOK and Future Crash keep separate personalities, memories, permissions, and tool contracts.
- Explicit Future Crash Ask/Workstation activity registers an interactive inference lease with Living AI.
- Future Crash ambient observations, automatic fortunes, scheduled model Threads, and private memory consolidation enter only when Living AI reports the shared background lane idle.
- Thread repair passes count as continuations of already-admitted work and are not stranded between frames.
- If Living AI is unavailable, Future Crash remains standalone and behaves normally.

The rule is: **one inference infrastructure, several distinct minds.**


### Living Memory receipts

`lk memory` now reports the result of background extraction as well as queue state. Model extraction remains primary, with a conservative deterministic fallback for obvious user preferences and project-state statements so a small/local model cannot leave candidate memory inert merely by returning `NONE` repeatedly.


### Living Memory reinforcement

Repeated equivalent evidence now increments candidate USES and importance, and strong overlap with an active candidate can reinforce it even when model extraction returns NONE.


### AI performance

`lk ai stats` shows rolling LO latency and throughput telemetry plus current Ollama model residency/VRAM information. LOOK stores only timings, token counts, rounds and tool counts—not conversation content.


### Warm model residency

Interactive LO keeps the selected Ollama model resident with `keep_alive=-1`, avoiding repeated cold-load penalties on dedicated local/remote AI hosts. `lk ai stats` marks tasks warm/cold and distinguishes GPU-resident model memory from model size.


### Destination fidelity and reveal

LO preserves explicitly named destination folders rather than silently substituting the current directory. `reveal_path` and `lk reveal PATH` open an existing path in the host file manager without adding another short command alias.


### Undo journal

`lk undo list` shows the current transaction stack with READY/BLOCKED state. `lk undo skip` explicitly abandons only the newest BLOCKED record; normal `lk undo` never skips history automatically.

### Terminal owner

LOOK, LO and Future Crash use the terminal/tab title as a lightweight ownership indicator while active.


### LO filesystem access

The starting folder is LO's default trusted workspace. Outside paths can be granted once, for the session, permanently, or through the Personal preset (`~/Desktop`, `~/Documents`, `~/Downloads`). `lk access` shows and manages persistent grants. Permission is enforced by LOOK itself rather than model judgment.


### Living Memory compiler

LOOK 4.3 uses a layered memory model: disposable candidates, durable atomic memories, compact semantic-domain summaries, and a tiny routing summary. Only relevant memory is retrieved into a normal LO prompt. The resident Living AI broker periodically compacts durable memory during idle time without broadening user claims.


### POWER command authority

POWER mode distinguishes known read-only inspections from potentially mutating shell work. Safe inspections can run directly; other commands use LOOK's native once/session confirmation UI. Models never negotiate shell authorization conversationally. `lk ollama test` reports natural AGENT execution separately from controlled tool judgment.


### Desktop bridge

LOOK can hand artifacts out of the terminal without teaching the model platform-specific application commands. `lk open`, `lk preview`, and `lk reveal` use OS defaults or optional category preferences managed by `lk apps`. LO exposes the same actions as host-owned read-only tools subject to normal path grants.


### Shell namespace

LOOK's canonical namespace is `lk`. The fast collision-resistant view commands are `lkl`, `lkd`, `lkf`, `lkt`, `lkr`, and `lkz`. Ultra-short aliases such as `ll`, `lr`, and `lz` are installed only when their names are available under the current shortcut policy. `lk shortcuts` shows or changes that policy. LOOK never deliberately shadows a builtin or an executable on PATH.


### Model runtime fit

`lk ollama test` reports capability and interactive runtime separately. `FIT` is based on broad warm TTFT/generation-rate thresholds (EXCELLENT, GOOD, SLOW, POOR). A POOR result is a prompt to inspect `lk ai stats` and `ollama ps`; timing alone is not treated as proof of GPU spill.

`lk ollama test --all` is the platform qualification sweep: disabled models are skipped, each enabled model is tested alone at 4096 context, cold load time is separated from a three-sample warm median, and the prior resident set is restored afterward. Run it locally on each node so the resulting benchmark describes that machine. `lk ollama curate` then combines those node-local measurements with the node-local enabled/disabled model policy and current GPU pressure.


### Settings control room

`lk settings` is the human-facing configuration surface. It is searchable: begin typing any concept such as `memory`, `video`, `GPU`, `safe`, `sound`, or `downloads`, and the list narrows to the relevant control. The right-hand preview explains what the highlighted setting does before you change it.

You can also enter with a search already applied:

```text
lk settings memory
lk settings video
lk settings gpu
lk settings shortcuts
```

Direct commands remain available for scripting and muscle memory; the control room calls the same underlying functions rather than maintaining a second settings system.


### Vision, generative media, scheduler

Vision-capable Ollama models can receive explicit local image paths in normal LO chat, or through `lk vision`. Optional ComfyUI integration is configured through `lk comfy`; existing installs/model folders can be discovered and reused, while large image checkpoints are never downloaded automatically. Persistent delayed and recurring work is available through `lk schedule` and is dispatched by the resident Living AI service into the normal LO background-job queue.


### GPU workstation bootstrap

On Linux + NVIDIA systems, the installer offers managed ComfyUI setup. It discovers old Comfy/A1111 model libraries on the home directory and common mounted-drive roots before installing anything, can reuse those weights through Comfy's external model paths, and offers explicit verified starter downloads. `lk comfy bootstrap` reruns the setup later; `lk comfy start|stop|restart` manages the local service. SDXL is the ready-to-run workflow starter; FLUX.1 Schnell FP8 is available as an optional modern checkpoint.


### Services and tailnet sharing

`lk services` is the unified view of local LOOK services and their private Tailscale Serve endpoints. `lk share` exposes every configured service currently running on the machine; Ollama and Comfy use separate dedicated HTTPS ports so they can coexist. Mercury Writer can be discovered when its running process exposes a port or configured explicitly with `lk services set mercury PORT`.

## 4.1 Fabric Pulse / 4.1.1 Fabric Truth

Every installed machine is now a peer in the Future Crash compute fabric. `lk fabric` shows the local supervisor, peers and warm models; `lk fabric models` shows model capability advertisements; `lk fabric pulse` exposes the shared reconciliation beat. Immediate work remains asynchronous—the pulse exists to refresh truth and recover from stale state, not to slow the network into lockstep.


## 4.5 Fabric application integration

Fabric-native work routes automatically across live capable nodes. The LOOK Ollama host setting is retained only as a direct-inference compatibility/debug override. **Local preferred model is machine-local**: its picker always comes from `127.0.0.1:11434`; a legacy remote host keeps its own separate direct-host preference and neither setting controls Fabric automatic placement. Signal browser sessions run visual expression in parallel with LO and present surfaced images/PDFs/files back to the requesting browser instead of opening them on the worker desktop. Future Crash Ask/Workstation use a canonical Open-Meteo weather edge for live weather.

## 5.1 Fabric lights + Signal-first visuals

Run `lk dash` on several nodes and open Signal on a phone/tablet, then try `lk fabric lights demo`. `lk fabric lights disco` and `christmas` repeat until Ctrl-C; the show is a pulse-derived lease, not a streamed animation. Signal scenes are the default lightweight visual expression channel; explicit draw/generate/picture/artwork requests use Comfy and generated image artifacts are presented inline in Signal.

## Experimental greenfield fork brief

The stable project remains intentionally plural: LOOK/`lk` is the Unix tool, LO is the cognitive work network, Future Crash is the retro ambient interface, and Signal is the browser-native instrument. `docs/GREENFIELD_FORK.md` captures the separate “start over without starting over” experiment: capability-oriented Fabric workers beyond Ollama, heterogeneous/dual-resident inference, ephemeral browser/WebGPU workers, small-model cognitive maintenance, provenance, and Show Work demos. It is a design brief, not a production migration plan.
## Shared Fabric UI model (5.2.14)

Fabric now publishes a small renderer-neutral `fabric-ui-v1` state document at `/v1/ui/state`. Dash consumes the same action/capability vocabulary that Signal and Future Crash can reuse later. The intent is deliberately incremental: keep ANSI terminal and vanilla web renderers, while centralizing meaning rather than adopting a heavyweight TUI/web framework.

## Streaming artifacts + media proof (5.2.15)

Fabric artifacts can now be file-backed as well as small managed blobs. `fcl-node artifact-add PATH` hashes an existing file and records its node-local location without copying the bytes into Fabric state. The artifact endpoint supports HTTP byte ranges, so a consumer can seek through a large movie, recording, dataset, or music file without downloading it first. Nodes advertise this as `artifact.read`, `artifact.range`, and `artifact.stream`; media is only the first visible consumer.

LOOK keeps playback deliberately thin. Same-node files take the cheapest path directly to `mpv`; `lk media stream PATH` is the explicit artifact/range-stream proof, while remote SHA entries stream through Fabric. The historical `lk media play` with no path remains a play/pause transport control. `lk media add PATH` and `lk media info [@NODE] DIGEST` expose the underlying artifact for testing. VLC/system playback remains a fallback.

In 5.2.17 the library view becomes Fabric-wide without becoming a media application. `/v1/media/catalog` publishes one node's cheap scan index and `/v1/media/fabric` unions online nodes. SHA-identified duplicates collapse logically while retaining their physical locations; shell completion and the LOOK media selector consume that same catalog.

```text
source node                     playback node
───────────                     ─────────────
file → artifact identity → HTTP Range stream → mpv/browser

Signal keeps playback output selection on the active media card. Fabric nodes expose playback readiness and reasons for unavailability; an ephemeral **This Device** browser endpoint can stream the same queue without becoming a full compute node.
       sha256:...
```

No media root is hard-coded. A future storage audit can move the 3090 library onto a clean `/srv/...` layout and re-register/reindex locations without changing consumers or Fabric identity semantics.

