## 2.0.3 — Deterministic inspection + reinforced learning

- Added `inspect_directory`, a bounded read-only filesystem tool for exact file/folder/symlink counts, recursive counts, file bytes, truncation status, and elapsed time.
- LO is explicitly instructed to prefer deterministic directory inspection over listing entries and counting them in model context.
- `inspect_directory` is available even in Conservative access because it is read-only and workspace-bounded.
- Natural positive/negative feedback such as “great job” or “that didn’t work” can now trigger detached background reflection on the immediately preceding interaction.
- Feedback reflection is conservative: it may return NONE, NEW, REINFORCE, WEAKEN, or CORRECT.
- Learned skills remain human-readable in `skills.md`; reinforcement metadata lives separately in `skill_state.json`.
- Skill metadata tracks confidence, positive hits, negative hits, creation time, and last reinforcement.
- Confidence-zero learned skills remain inspectable on disk but are omitted from LO’s active skill prompt.
- Added `lk skills state` to inspect reinforcement state.
- `lk skills export` now includes a reinforcement-state appendix.
- `skill_state.json` is part of the portable LOOK profile; feedback queues/locks remain runtime state and are excluded.
- Substantive learning emits a normal LOOK event; NONE stays silent.
- Future Crash remains 1.1.7.

## 2.0.2 — Give LO room to finish

- Replaced the single 8k / 5-round LO runtime ceiling with task-tiered FAST, STANDARD, and DEEP budgets.
- FAST: 8k context, 1,500 output tokens, 4 tool rounds.
- STANDARD: 16k context, 3,500 output tokens, 8 tool rounds.
- DEEP: 24k context, 6,000 output tokens, 12 tool rounds.
- Budgets are ceilings, not targets; short requests still stop naturally when complete.
- Adaptive task classification considers request structure, length, selected-file count, and explicit deep-thinking mode.
- Conversation working history headroom increased from 20 messages / 14k characters to 28 messages / 28k characters.
- Thinking policy remains independent from budget selection.
- Added `lk budget <request>` as an inspectable tuning aid.
- Future Crash remains 1.1.7.

## 2.0.1 — Information receipts

- Added canonical DATA (Wikidata), PAPERS (Crossref), and ARCHIVE (Internet Archive) LO information edges.
- WEATHER, PLACE, WIKI, DATA, PAPERS, and ARCHIVE now return a common provenance envelope.
- Added DIRECT / DERIVED / SEARCHED / MODEL epistemic vocabulary; no fake confidence percentages.
- LO is instructed to prefer canonical edges over generic search when the question fits.
- Added `docs/LIVING-WITH-LOOK.md`, a human-oriented description of ordinary use rather than another command manual.
- Added `docs/INFORMATION-EDGES.md` documenting the source/provenance contract.
- Future Crash remains 1.1.7.

## 2.0.0 — Portable identity

LOOK 2.0 formalizes four kinds of state:

- **Program** — versioned code/defaults from the distribution.
- **Profile** — the user's evolving AI identity: memory, continuity, core, skills, personalities, behavior preferences, and expression settings.
- **Machine** — secrets, host/network configuration, local services and hardware-specific state.
- **Runtime** — undo/trash, jobs/events, queues, locks, PIDs, caches.

### Portable profile

- Added `lk profile` status and inventory.
- Added `lk profile backup [DEST] [--keep N]` with remembered backup destination and rotating snapshots.
- Added `lk profile export [ZIP]` for migration.
- Added `lk profile restore <ZIP|BACKUP_DIR>` with schema validation and a local pre-restore safety snapshot.
- Secrets, undo/trash, jobs/events, queues/locks/PIDs, generated caches, and machine-specific Ollama host plumbing are deliberately excluded.
- Profile archives are schema-versioned for future migration.
- Added `lk skills export [FILE]` to export only locally learned skills for review/promotion into later distributions.

### Terminal expression

- Added centralized finite feedback events rather than scattered animation/sound calls.
- `lk feedback` manages sound and motion; `lk sound` is the fast sound toggle.
- Sound defaults **off**. Motion defaults **subtle**.
- Feedback never animates or sounds in piped/non-TTY output.
- Feedback tones are synthesized locally at runtime; no media assets are bundled.
- Batch completion/failure, profile operations, and background LO events use the shared feedback vocabulary.
- Settings/config surfaces expose profile and expression state.

Future Crash remains 1.1.7.

## 1.9.3 — Streaming global find

- Restored `f` and `fznv` to a streaming search architecture: `fd/find` feeds fzf while the user types immediately.
- Removed the blocking full-home catalog build that made global find appear hung for several seconds.
- Styled the streaming finder to match LOOK's cyan/dark visual language, including pointer, marker, spinner, and inline match count.
- `f` still hands the exact selected result into LOOK's normal filer/action interface.
- `fznv` still opens the selected path directly in Neovim.
- Future Crash remains 1.1.7.

## 1.9.2 — Truthful file-action exit codes

- Private LOOK file-action commands now return nonzero when copy/move/remove/mkdir/touch did not complete.
- `CREATE_DIR_REQUIRED`, cancellation, refusal, and failure no longer print failure text while returning shell status 0.
- This makes scripted regression checks reliable and improves shell composition.
- Future Crash remains 1.1.7.

## 1.9.1 — Transaction-safe batch file actions

- Fixed multi-source `lmv`/`lcp` failures when the bounded undo journal was already full.
- Batch membership is now tracked with an explicit transaction ID rather than inferred from undo-list length.
- Temporary per-item batch receipts may exceed the normal 20-entry undo cap until commit, then collapse to one batch undo record.
- Missing destination directories created during a batch remain part of that transaction and are removed again on undo/rollback when empty.
- Batch success receipts identify the files actually moved/copied; large batches show the first 12 plus a remainder count.
- Batch failure receipts now name the source where failure occurred, the reason, and rollback status.
- Interactive LOOK file prompts retain Tab completion but now use a dedicated ZLE keymap where bare Escape cleanly cancels `lcp`, `lmv`, `lmk`, and related prompts.
- Future Crash remains 1.1.7.

## 1.9.0 — Completion, native find, temporal memory, LO jobs/events

- Filer copy/move destination prompts now support Tab path completion for relative, absolute, and `~` paths.
- Simplified Zsh completion for `lcp`, `lmv`, `lrm`, and `lscp`: every operand uses native repeated filesystem completion.
- `f` is now LOOK-native global find from `$HOME`, preserving fast `fd` cataloging when available while using LOOK's filter/preview/action interface.
- `fznv` uses the same LOOK-native global finder and hands the chosen file to Neovim.
- Recent LO exchanges now expose human-readable age to the model.
- Semantic memory candidates now store `created_at` and `last_reinforced`, and their age is visible to LO.
- LO's prompt contract now states that memory is historical context, never a pending-task queue. Old unfinished requests must not be resumed unless the current turn clearly asks to continue.
- Added durable `jobs/` and `events/` channels under LOOK state.
- `lo bg REQUEST` queues one-shot background LO work.
- Completed/failed jobs emit terminal events; the shell surfaces pending LO events automatically at the next prompt.
- Added `lk jobs` and `lk events` inspection commands.
- The queue/event contract is intentionally daemon-free for now; it can later sit behind a Unix socket or localhost service without changing callers.
- Future Crash remains 1.1.7.

## 1.8.2 — Active-row contrast

- Increased filer active-row contrast with a bright cyan selection band and dark text.
- Classic-color fallback now uses bold reverse video.
- No navigation or working-set behavior changed.
- Future Crash remains 1.1.7.

## 1.8.1 — Filter J/K collision fix

- Lowercase `j` and `k` are searchable characters again while actively typing a filter.
- In filter-entry mode, Shift-J / Shift-K (`J` / `K`) and the arrow keys move the highlighted match.
- Outside filter entry, ordinary lowercase `j/k` navigation remains unchanged.
- Future Crash remains 1.1.7.

## 1.8.0 — Persistent filer working set

- Filer selections now survive directory navigation. Mark files/folders in one location, move elsewhere, and continue adding to the same working set.
- `Tab` toggles one item; `A` toggles current matches; `X` clears the entire working set.
- Copy, move, remove, path-copy, clipboard, and LO-context actions operate on the persistent set when it is non-empty.
- Selection status is green when all selected items are visible in the current directory and amber when the set spans locations: `SELECTED · N / H HERE`.
- Parent navigation changed from `>` to `<` (Shift-,), matching the out/left mental model.
- Enter retains normal open/descend behavior.
- Documentation and installer metadata updated for the Git-ready release.
- Future Crash remains 1.1.7.

## 1.7.0 — Parent navigation

- Added `>` (Shift-.) in the plain filer browse state to move up one filesystem directory.
- This is distinct from Escape/back history: `>` means actual parent (`..`), while Escape still means back through LOOK navigation history.
- `>` remains an ordinary printable character while actively typing a filter, so search punctuation is not stolen.
- The current directory redraws immediately after moving up; entering another directory or using `G` keeps the existing shell-directory handoff behavior.
- Version rolled to 1.7.0 after the 1.6.x stabilization run.
- Future Crash remains 1.1.7.

## 1.6.16 — Filer navigation cleanup

- Fixed the `L` collision in FILTER/SELECT views: `L` is now exclusively the LO-context handoff.
- Removed the accidental `J/K/L/;` pseudo-direction scheme.
- Filer movement is now simply `j/k` (or `J/K`) and the up/down arrows.
- Updated help/documentation to match the actual controls.
- Future Crash remains 1.1.7.

## 1.6.15 — Filer → LO context handoff

- Added `L` / Shift-L in LOOK's FILTER and SELECT views.
- The current marked set is handed to a new LO session as explicit path context; with no marked set, the highlighted path is used.
- LO does not preload file contents. It receives an authoritative path manifest and uses existing bounded file tools only as needed.
- The LO workspace becomes the selected paths' nearest common directory, keeping every handed-off path inside its tool boundary.
- LO startup now reports `context · N selected paths`.
- Updated starter help, complete help, README, LOOK README, man page, and release notes.
- Future Crash remains 1.1.7.

## 1.6.14 — Tool receipts, not tool stories

- Added a host-side execution contract for explicit filesystem mutation requests. A prose-only answer is silently rejected once and retried as a tool-required turn.
- If the model still does not call a mutation tool, LOOK reports that no filesystem action was executed instead of allowing a fabricated success claim.
- Increased the LO tool loop from four to five rounds so create-directory → batch-create → final-report workflows have enough room.
- Added read-only `list_processes`, `listening_ports`, and `system_snapshot` tools to every LO access profile, including Workspace.
- Workspace still does not receive arbitrary shell execution; Power/Unsafe remain the boundary for `run_command`.
- Future Crash remains 1.1.7.

## 1.6.13 — Multi-source wrapper fix

- Fixed `lmv` multi-source argument slicing: the final destination is now explicitly popped from the source array before calling LOOK's batch mover.
- Applied the same explicit destination-pop logic to `lcp` for symmetry and future safety.
- The underlying batch/undo engine was already correct; failed self-move attempts were rolled back safely.
- Future Crash remains 1.1.7.

## 1.6.12 — Continuity + batch reliability

- `lk commands` now uses LOOK's existing terminal pager when it exceeds the screen; compact help uses the same no-op-when-short pager path.
- Added a separate literal recent-conversation ring for LO: the last completed exchanges persist immediately across `lo` sessions and are injected under a strict context budget.
- Candidate memory remains semantic and decaying; reaching zero means forgetting, not promotion.
- Long-term summary consolidation now runs periodically from still-strong/repeated candidates instead of waiting for an unrealistic cluster of 75+ scores.
- `lk memory` now shows recent cross-session turns separately from semantic candidates; `lk memory clear-recent` clears only literal recent continuity.
- Added bounded `create_text_files` for up to 32 new UTF-8 files in one verified tool call, with no overwrite, rollback on partial failure, and one undo transaction.
- `lcp` and `lmv` now accept multiple sources with the final argument as destination; `lrm` accepts multiple paths and confirms once.
- Existing filer multi-selection/batch actions were already correct and are intentionally unchanged.
- Future Crash remains 1.1.7.

## 1.6.11 — Starter control surfaces

- Added optional interactive `lk system`, `lk ai`, `lk net`, `lk clean`, and `lk config` control surfaces over existing LOOK commands.
- Added `lk commands` as a terse vocabulary index.
- `lk help` is now the compact starter toolkit; `lk help all` preserves the complete glossary.
- Added direct convenience aliases `lk models`, `lk benchmark`, and `lk web`.
- Existing expert commands remain available; the new layer is additive.
- `lk network` remains the direct address inspector; `lk config paths` preserves the raw installed-path view.
- Future Crash remains 1.1.7.

## 1.6.10 — Two games that are not installed

- Added two deliberately undocumented LOOK Easter eggs: `lk ttt` and `lk gtnw`.
- `lk ttt` is a full-screen blue-CRT tic-tac-toe game with a perfect minimax opponent.
- Tic-tac-toe accepts both `1–9` numpad geometry and the laptop-friendly `U I O / J K L / M , .` grid; `r` restarts and `esc` exits.
- `lk gtnw` is a randomized fictional WOPR-style terminal simulation with an abstract world map, animated red/blue trajectories, counters, speed control, restart, and escape. It contains no real target selection or operational data.
- `lk games` insists that no games are installed. Neither game appears in help.
- LOOK home has a very low-probability `SHALL WE PLAY A GAME?` line.
- Future Crash remains 1.1.7.

## 1.6.9 — LO information edges

- Added three canonical, read-only information tools to LO: live weather, geographic place lookup, and Wikipedia lookup.
- Weather and place resolution use Open-Meteo directly and require no API key.
- Stable encyclopedic questions can use Wikipedia's machine-readable search API instead of generic web snippets.
- Generic Ollama web search remains the broad fallback for current and open-ended research.
- Tool activity is visible as `weather ›`, `place ›`, or `wiki ›` while retrieval is in flight.
- Canonical tools are available even when `OLLAMA_API_KEY` is absent; only generic web search depends on that key.
- Future Crash remains 1.1.7.

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
