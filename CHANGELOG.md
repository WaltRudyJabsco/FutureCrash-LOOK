## 1.6.8 — Explicit LO model budgets

- Gives LO an explicit 8192-token working context and bounded recent conversation history instead of allowing the transcript to grow indefinitely.
- Makes `lk thinking light/adaptive/deep` control Ollama reasoning behavior when the selected model advertises thinking support.
- Uses generous interactive ceilings: 800 tokens light, 1400 adaptive, and 2000 deep.
- Adaptive thinking stays immediate for simple conversation and escalates for clearly analytical, debugging, coding, or multi-step requests.
- Gives memory extraction, skill extraction, and summary maintenance small explicit no-thinking budgets so background housekeeping cannot waste hidden deliberation.
- Keeps capability/tool behavior unchanged; this release changes model-resource policy, not permissions.

## 1.6.7 — Conversation/render budget split

- Routes explicit Signal requests directly to a dedicated no-thinking Signal compiler instead of making Workstation narration and rendering compete for one response.
- Signal compile/repair gets 1200 output tokens at temperature 0.25; ordinary Workstation gets 1600, Quick Ask 400, and ordinary Threads 300.
- Visual Threads use the same Signal compiler while retaining their verified host receipt and recent Signal receipt.
- Signal compilation receives only the visual request and recent Signal feedback, not unrelated conversation/memory context.
- Keeps one silent repair pass if the dedicated compiler still returns malformed Signal.

## 1.6.7 — Conversation/render budget split

- Routes explicit Signal requests directly to a dedicated no-thinking Signal compiler instead of making Workstation narration and rendering compete for one response.
- Signal compile/repair gets 1200 output tokens at temperature 0.25; ordinary Workstation gets 1600, Quick Ask 400, and ordinary Threads 300.
- Visual Threads use the same Signal compiler while retaining their verified host receipt and recent Signal receipt.
- Signal compilation receives only the visual request and recent Signal feedback, not unrelated conversation/memory context.
- Keeps one silent repair pass if the dedicated compiler still returns malformed Signal.

## 1.6.6 — Persistent activity + full Signal compile budget

- Added LOOK-style cyan `◐ ◓ ◑ ◒` activity feedback across Future Crash views while Oracle work is in flight.
- Activity state survives leaving Workstation, so `esc` can return to Ambient without making a running request look stalled or cancelled.
- Labels distinguish Workstation, Oracle, Thread, Memory, Fortune, and Signal compiler activity.
- Fixed the Signal repair pass output budget: complex sprites/animations now receive 600 output tokens instead of the generic 64-token fallback.
- Signal repair runs without model reasoning so the budget is spent on the display program itself.
- LOOK behavior is otherwise unchanged.

## 1.6.5 — Signal protocol completion

- Treat visual requests as incomplete until a parseable `[[SIGNAL]]` program is actually received.
- Add one silent Signal compiler-repair pass for Workstation, Quick Oracle, and visual Threads.
- Suppress prose-only planning chatter from failed visual Thread attempts instead of presenting it as completed work.
- Keep the existing deterministic framebuffer/animation renderer; no model-driven timing loop added.
- Normalize Workstation control hints to lowercase key labels.
- Correct installer/version metadata drift from earlier 1.6.x packaging.

## 1.6.3

- Fix Signal fallback-dream receipt crash introduced in 1.6.2 by centralizing Signal receipt stats initialization.

# Future Crash + LOOK changelog

## 1.6.2 — raster Signal Field

- Teaches Signal its full 40x12 addressable character-framebuffer mental model.
- Adds whitespace-preserving `SPRITE` raster art and host-rasterized normalized `BARS`.
- Signal receipts now report render modes, nonempty-cell count, and occupied dimensions.
- Animation frames may freely mix semantic, vector, and raster primitives.


## 1.6.1 — Signal wiring fix

- Preserves Signal directives from structured model thinking and restores the larger Workstation/Oracle Signal pane.
- Dream wakes now always produce visible Signal activity.


## 1.6.0 — expressive Signal Field

- Adds Signal render receipts, feedback context, tiny animation frames, and a built-in dream thread preset.
- Future Crash recent memory expands modestly from 5 to 8 exchanges before consolidation.


## 1.5.4 — bottom anchoring

- Pins Fortune/menu to the terminal bottom and returns unused height to the main panels.


## 1.5.3 — Fortune visual polish

- Gives Fortune a fixed label + three-line body so the ambient layout no longer jumps.
- Loosens fortune length and hardens final-only cleanup.


## 1.5.2 — Future Crash artifact hardening

- Fixes the runtime Future Crash version header.
- Rejects reasoning/prompt paraphrase in fortune and ambient micro-generations and falls back locally.


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

## 1.6.4

- Signal is now a persistent CRT-style display by default; `TTL` is opt-in for temporary imagery.
- Signal playback remains host-timed and continues independently of the Workstation conversation.
- Added a subtle continuous CRT scan glow over active Signal content.
- Visual-request detection now recognizes Signal/animation/sprite/EQ/dashboard language and explicitly requires emitted Signal code rather than prose-only discussion.
