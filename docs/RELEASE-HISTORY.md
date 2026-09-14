# Release History

Consolidated historical release notes for Future Crash + LOOK.

The current release keeps its own standalone note in `RELEASE-2.7.2.md`; older notes are preserved below to keep the repository small and Git-friendly.


---

<!-- source: RELEASE-1.0.2.md -->

# 1.0.2 — Terminal Experience

Optional reference presentation layer:
- macOS: iTerm2
- Linux: Kitty
- Powerlevel10k
- MesloLGS NF

Core installation remains independent. Existing terminal preferences and prompt configuration remain user-owned.


---

<!-- source: RELEASE-1.1.1.md -->

# 1.1.1 — Documentation synchronization

No memory architecture changes.

Synchronized the 1.1 memory/skills vocabulary across:
- top-level README
- LOOK README
- `lk help`
- `look/docs/COMMANDS.md`
- `man lk`
- LO memory design documentation

Also updates the man-page version label and unified uninstall wording.


---

<!-- source: RELEASE-1.1.2.md -->

# 1.1.2 — installer platform detection fix

Fixes `install.sh: OS: unbound variable` in the optional Terminal Experience stage.

The terminal setup now derives its own platform value with `uname -s` instead of depending on a global installer variable.

No runtime, memory, capability, LOOK, Future Crash, or AI behavior changed.


---

<!-- source: RELEASE-1.1.3.md -->

# 1.1.3 — Memory sanitation

- Strip paired and orphaned Qwen thinking output before persistence.
- Candidate worker fails closed unless output is exactly `NONE` or `NN|text`.
- Reject common model-meta/reasoning patterns.
- Invalid summary rewrites retain the previous clean summary.
- Existing contaminated candidates are pruned automatically on memory load.
- Adds `lk memory prune` and `lk memory clear-summary`.
- Candidate limits, importance, decay, and skills architecture are unchanged.


---

<!-- source: RELEASE-1.1.4.md -->

# 1.1.4 — Conversational continuity + nesting guard

## Memory
- Candidate capture is intentionally less conservative.
- Preferences, favorites, habits, project decisions/state, unresolved tasks, and explicit memory requests are normally remembered.
- Importance guidance now distinguishes recent continuity from durable preference.
- Explicit phrases such as `remember this`, `this is important`, `one of my favorites`, `I really like`, and `I prefer` receive a deterministic fallback when the semantic worker returns `NONE`.
- Existing decay, sanitation, 20-candidate cap, 8-memory attention cap, and long-term summary behavior are unchanged.

## Future Crash
- Prevents accidental recursive Future Crash nesting.
- Shells entered from Future Crash inherit `FUTURE_CRASH_ACTIVE=1`.
- `fc`, `rst`, and `future-crash` refuse to launch another normal instance while already inside one.
- `future-crash --nested` remains an explicit escape hatch.


---

<!-- source: RELEASE-1.1.5.md -->

# 1.1.5 — Conversation-first LO + self-learning craft

## Conversation
- Casual conversation/general knowledge no longer triggers workspace inspection merely because tools exist.
- Relevant memories are used naturally; importance scores are not surfaced unless requested.
- `lo` is now `noglob lk o`, making `?`, `*`, and bracket glob characters safe in one-shot prompts.
- Unmatched shell quotes remain a Zsh parsing limitation; interactive `lo` is the unrestricted prose path.

## Memory
- User-memory extraction is explicitly grounded in what the user said or clearly confirmed.
- Assistant suggestions are not promoted into user preferences from acknowledgements such as `nice`.

## Skills
- LO can autonomously learn rare, generalized assistant craft into `skills.md`.
- Automatic learning is disabled in Conservative and enabled in Workspace/Power/Unsafe.
- Skill output must be exactly `NONE` or `SKILL|lesson` and is sanitized, deduplicated, capped at 24, inspectable, editable, and reversible.
- Adds `lk skills add`, `lk skills forget`, and `lk skills clear-learned`.


---

<!-- source: RELEASE-1.1.6.md -->

# 1.1.6 — Interactive input editing

- Enables Python readline/libedit support for LO's `you ›` prompt.
- Restores normal left/right cursor movement and line editing.
- Enables history up/down and Home/End where supported.
- Falls back silently if readline/libedit is unavailable.
- No memory, skills, model, tool, capability, or routing behavior changed.


---

<!-- source: RELEASE-1.2.0.md -->

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


---

<!-- source: RELEASE-1.2.1.md -->

# 1.2.1 — Durable memory promotion + long-term pruning

- LO no longer falsely claims explicit memory requests are session-only.
- Explicit durable phrases trigger immediate long-term-summary promotion.
- Durable candidate importance is raised to at least 90.
- Obvious duplicate candidates consolidate before summary promotion.
- Long-term summary is periodically rebuilt every 12 maintenance cycles.
- Summary maintenance is capped at 180 words and may forget stale, redundant, superseded, or low-value facts.
- Candidate decay/reinforcement and skills are unchanged.

Versions:
- Future Crash + LOOK 1.2.1
- LOOK 3.5.1
- Future Crash 1.0.0


---

<!-- source: RELEASE-1.3.0.md -->

# 1.3.0 — Media transport + versioned intelligence

Versions:
- Future Crash + LOOK 1.3.0
- LOOK 3.6.0
- Future Crash 1.0.0
- Memory schema 1
- Skills schema 1
- Bundled skills pack 1

## Media
- Adds `lk media [status|toggle|next|prev|stop]`.
- macOS adapter supports running Music and Spotify.
- Linux adapter uses MPRIS through `playerctl`.
- Adds Zsh completion and documentation for media actions.

## Intelligence versioning
- Memory JSON now carries `schema_version`.
- Skills Markdown now carries `schema` and `bundled-version` metadata.
- `lk skills version` reports the installed craft layer.
- `lk skills update [FILE]` replaces compatible Bundled craft while preserving Learned craft.
- Existing pre-versioned skills files are upgraded without losing their Learned section.

## README
- Rewritten as a new-user guide instead of accumulated release archaeology.
- Restores explicit `chmod +x install.sh` explanation.
- Preserves the screenshot paths supplied for the GitHub repository.


---

<!-- source: RELEASE-1.3.1.md -->

# 1.3.1 — Fast media aliases + paged intelligence views

- Adds `mm` → `lk media toggle`.
- Adds `mn` → `lk media next`.
- Adds `mp` → `lk media prev`.
- `lk memory` now uses LOOK's pager for long output.
- `lk skills` now uses LOOK's pager for long output.
- No memory, skills, AI, permission, or media-adapter semantics changed.

Versions:
- Future Crash + LOOK 1.3.1
- LOOK 3.6.1
- Future Crash 1.0.0


---

<!-- source: RELEASE-1.3.2.md -->

# 1.3.2 — macOS media detection fix

- Removes the brittle System Events process check from `lk media`.
- Uses direct AppleScript `application "Music" is running` / `application "Spotify" is running` checks.
- Queries and controls the running app directly after detection.
- `mm`, `mn`, and `mp` are unchanged.
- Paging, memory, skills, AI, and capability behavior are unchanged.


---

<!-- source: RELEASE-1.3.3.md -->

# 1.3.3 — direct macOS media transport

- Guards and controls an already-open Music or Spotify instance in one AppleScript call.
- Does not launch a player merely to satisfy a media command.
- `mm`, `mn`, `mp`, paging, memory and skills are otherwise unchanged.


---

<!-- source: RELEASE-1.3.4.md -->

# 1.3.4 — media status feedback

- Replaces the combined macOS status script with direct queries for player state, artist, and track name.
- `lk media` shows current player/state/track.
- `mm`, `mn`, `mp`, and full media transport commands now print the resulting state/track after success.
- macOS media commands only control already-open Music or Spotify instances; they do not launch a player.
- All aliases/help/README/man/command docs are synchronized.


---

<!-- source: RELEASE-1.4.0.md -->

# 1.4.0 — LOOK smart make

Versions:
- Future Crash + LOOK 1.4.0
- LOOK 3.7.0
- Future Crash 1.0.0

## Smart make
- `lmk FILE.ext` creates an empty journaled file.
- `lmk DIR/` creates a journaled directory and enters it.
- `lmk -f NAME` / `lmk -d NAME` provide explicit file/directory intent.
- Extensionless names prompt for directory vs file.
- Missing parent paths for file creation require confirmation.
- `mkd DIR` now delegates to `lmk -d DIR`.

## Undo
- New file creation is undoable only while the file remains empty and unchanged.
- Directory undo refuses once the directory is non-empty.
- Parent directories created as part of a LOOK make action are cleaned up when still empty.

## Completion
- Adds `_lmk` Zsh completion for explicit mode flags and parent-directory navigation.

Documentation/help/man/README have been synchronized.


---

<!-- source: RELEASE-1.4.1.md -->

# 1.4.1 — LOOK prompt input fix

- Fixes doubled characters in LOOK's character-at-a-time prompts by using silent raw reads.
- `lmk` ambiguity selection is now immediate single-key input: `d`, `f`, or Esc.
- Parent-path confirmation is now immediate `y` / `n`.
- No Enter is required for these choice prompts.
- General LOOK text prompts retain character editing without duplicate echo.

Versions:
- Future Crash + LOOK 1.4.1
- LOOK 3.7.1
- Future Crash 1.0.0


---

<!-- source: RELEASE-1.4.2.md -->

# 1.4.2 — lmk directory-entry fix

- `lmk -d NAME` no longer captures/parses LOOK's rendered mkdir output.
- Prompted directory creation uses the same direct path.
- Directory creation succeeds via `lk _mkdir`, then `lmk` enters the directory only after verifying it exists.
- Keeps the 1.4.1 single-key prompt fix.

Versions:
- Future Crash + LOOK 1.4.2
- LOOK 3.7.2
- Future Crash 1.0.0


---

<!-- source: RELEASE-1.5.0.md -->

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


---

<!-- source: RELEASE-1.5.1.md -->

# 1.5.1 — Future Crash final-only micro-generation

Versions:
- Future Crash + LOOK 1.5.1
- LOOK 3.8.0
- Future Crash 1.0.1

## Fixed
- Fortunes no longer display model reasoning.
- Oracle/ambient observations no longer display model reasoning.
- Handles normal `<think>...</think>`, structured Ollama `thinking`, and orphaned `</think>` template output.
- All Future Crash model output now passes through one shared final-answer extractor.

## Personality boundary
- Adds `future-crash/personality.md`.
- Future Crash keeps its own stable signal-field/workstation personality.
- LO's selectable personality does not leak into Future Crash.


---

<!-- source: RELEASE-1.5.2.md -->

# 1.5.2 — Future Crash artifact hardening

Versions:
- Future Crash + LOOK 1.5.2
- LOOK 3.8.0
- Future Crash 1.0.2

- Fixes the Future Crash runtime/header version constant.
- Fortunes and ambient observations reject obvious prompt-paraphrase/reasoning leakage.
- If a short model response contains reasoning but no usable final artifact, Future Crash falls back to its local fortune/observation seed.
- Conversational Ask/Work output still uses the normal final-answer extractor.


---

<!-- source: RELEASE-1.5.3.md -->

# 1.5.3 — Fortune layout + cleanup

Versions:
- Future Crash + LOOK 1.5.3
- LOOK 3.8.0
- Future Crash 1.0.3

- Fortune now has a fixed `FORTUNE //` label plus exactly three reserved body lines.
- Footer/menu position no longer jumps as fortunes wrap between one, two, or three lines.
- Fortune generation may use up to 36 words.
- Fortune prompt more strongly requires final artifact only.
- Fortune contamination detection catches remaining task/goal/instruction paraphrases.
- Fortune generation gets a slightly larger output budget so a final sentence is less likely to be truncated.


---

<!-- source: RELEASE-1.5.4.md -->

# 1.5.4 — Future Crash bottom anchoring

Versions:
- Future Crash + LOOK 1.5.4
- LOOK 3.8.0
- Future Crash 1.0.4

- Pins the fixed Fortune block and command menu to the bottom of the terminal.
- Returns all unused vertical space to TELEMETRY and SIGNAL.
- Removes the accidental blank rows beneath the command footer.
- Fortune remains a fixed label plus three body lines.


---

<!-- source: RELEASE-1.6.0.md -->

# 1.6.0 — Signal Field becomes expressive

Versions:
- Future Crash + LOOK 1.6.0
- LOOK 3.8.0
- Future Crash 1.1.0

## Signal
- Signal is now explicitly a native expressive channel for Ask and Workstation.
- Adds bounded persistent SIGNAL RECEIPTs (accepted/rejected commands, clipping, bounds, title, frames).
- Recent render receipts return to the model as visual-craft feedback.
- Adds tiny animation syntax with `FPS` and up to eight `FRAME` sections.
- Scheduled model-wake Threads receive recent Signal feedback.

## Dream preset
- Threads screen: `D` toggles a built-in ~4-minute SIGNAL DREAM preset.
- Dream thread uses model_wake and may remain visually expressive while returning SILENT prose.

## Memory
- Future Crash recent Workstation memory increases from 5 to 8 exchanges.
- Long-memory budget increases modestly while remaining bounded/compressed.


---

<!-- source: RELEASE-1.6.1.md -->

# 1.6.1 — Signal wiring fix

Versions:
- Future Crash + LOOK 1.6.1
- LOOK 3.8.0
- Future Crash 1.1.1

- Preserves valid `[[SIGNAL]]` blocks from structured model thinking while still hiding reasoning prose.
- Ask, Workstation, ambient, and scheduled Thread output can all reach the Signal parser.
- Restores a larger roughly 50/50 text/Signal layout in Oracle and Workstation views on desktop-width terminals.
- Removes the old 16-row cap from the desktop Signal pane.
- Built-in Dream requires a Signal render every wake.
- If a Dream wake returns no drawing, Future Crash renders a small host-side fallback dream instead of silently doing nothing.
- Ambient output rejects leaked Signal-language instructions as visible observation text.


---

<!-- source: RELEASE-1.6.2.md -->

# 1.6.2 — Raster Signal Field

Versions:
- Future Crash + LOOK 1.6.2
- LOOK 3.8.0
- Future Crash 1.1.2

Signal now exposes the mental model that was already latent in the renderer: a 40×12 addressable character framebuffer. The model can choose among semantic, vector, and raster representations instead of treating Signal as only a tiny vector API.

## New primitives

```text
BARS x baseline_y color 0.15 0.32 0.75 0.91

SPRITE x y color
  .----.
 / o  o \
|   --   |
 \______/
END
```

`BARS` accepts normalized 0..1 values and leaves deterministic rasterization to Python. `SPRITE` preserves leading/trailing whitespace and treats spaces as transparent cells, allowing compact ASCII/pixel art to layer over other primitives. Both work inside normal Signal blocks and animation `FRAME`s.

Signal receipts now include semantic/vector/raster mode usage, nonempty-cell count, and occupied dimensions in addition to clipping, bounds, title, accepted/rejected command counts, and frame count.


---

<!-- source: RELEASE-1.6.3.md -->

# Future Crash + LOOK 1.6.3

Surgical stability release.

## Fixed

Signal fallback dreams no longer crash when emitting a receipt. The 1.6.2 raster receipt work added a `modes` field to Signal statistics, but the fallback dream path still initialized the older stats shape. Signal stats now use one shared initializer for parser and fallback paths.


---

<!-- source: RELEASE-1.6.4.md -->

# Future Crash + LOOK 1.6.4

Signal CRT release.

## Changed

Signal now behaves like a tiny persistent display device rather than a temporary drawing panel. Model output defines framebuffer/animation state; Future Crash owns continuous scan and frame timing. Signal requests are recognized directly (`signal`, `animated`, `sprite`, `EQ`, `dashboard`, etc.), and animation requests explicitly require `FPS` plus multiple `FRAME` sections instead of prose-only discussion. `TTL` remains available for intentionally temporary displays.


---

<!-- source: RELEASE-1.6.5.md -->

# Future Crash + LOOK 1.6.5

Signal rendering was already alive; protocol compliance was the missing link. Visual requests now remain incomplete until Future Crash receives a parseable `[[SIGNAL]]` program. A prose-only attempt gets one silent compiler repair pass, including scheduled visual Threads. The framebuffer, scan effect, and FPS/FRAME playback remain deterministic host-side behavior. Workstation control hints are normalized to lowercase.


---

<!-- source: RELEASE-1.6.6.md -->

# Future Crash + LOOK 1.6.6

Future Crash 1.1.6 adds persistent LOOK-style activity feedback for background Oracle work and fixes the Signal compiler repair budget. A running request remains visibly alive after leaving Workstation, and complex animated Signal programs can now use up to 600 output tokens instead of the accidental 64-token cap. LOOK remains unchanged.


---

<!-- source: RELEASE-1.6.7.md -->

# Future Crash + LOOK 1.6.7

Future Crash 1.1.7 separates conversation from rendering. Explicit Signal requests now go directly to a focused no-thinking compiler with a 1200-token output ceiling, while ordinary Workstation conversation receives a 1600-token budget. Visual Threads use the same compiler and retain verified host/status receipts. LOOK is unchanged.


---

<!-- source: RELEASE-1.6.8.md -->

# Future Crash + LOOK 1.6.8

This release makes LO's model-resource policy explicit.

- LOOK 3.8.1
- Future Crash 1.1.7
- LO working context: 8192 tokens
- LO output ceilings: light 800, adaptive 1400, deep 2000
- Recent chat history is bounded by both message count and approximate serialized size.
- Thinking depth now controls the Ollama `think` field when the selected model reports thinking capability.
- Background memory, summary, and skill extraction run with small explicit no-thinking budgets.

The design goal is consistent behavior across a modest local laptop and a fast remote GPU: ceilings provide headroom, while short answers still stop naturally.


---

<!-- source: RELEASE-1.6.10.md -->

# Future Crash + LOOK 1.6.10

A tiny Easter-egg release. LOOK 3.9.1 adds two hidden terminal games: `lk ttt` and `lk gtnw`. They are intentionally absent from help; `lk games` claims none are installed. Future Crash remains 1.1.7.


---

<!-- source: RELEASE-1.6.11.md -->

# Future Crash + LOOK 1.6.11

This release adds a human-sized navigation layer without removing LOOK's direct vocabulary.

Start with `lk system`, `lk ai`, `lk net`, `lk clean`, or `lk config`. Each is a small keyboard control surface over commands that already existed. `lk help` teaches the starter toolkit, `lk commands` is the terse index, and `lk help all` retains the full reference.

Future Crash remains 1.1.7. LOOK is 3.10.0.


---

<!-- source: RELEASE-1.6.12.md -->

# Future Crash + LOOK 1.6.12

This release separates three kinds of continuity:

1. **Recent conversation** — literal completed exchanges, persisted immediately across LO sessions.
2. **Candidate memory** — semantic notes with importance and natural decay.
3. **Long-term memory** — a compact background consolidation of candidates that remain useful.

A candidate reaching zero is forgotten; it is not promoted. Long-term consolidation happens while candidates are still strong or reinforced.

LO also gains one deterministic multi-file creation tool (`create_text_files`, maximum 32 new text files) and the shell helpers `lcp`, `lmv`, and `lrm` accept multiple paths. LOOK's existing filer batch-selection machinery is unchanged.

LOOK is 3.10.1. Future Crash remains 1.1.7.


---

<!-- source: RELEASE-1.6.13.md -->

# Future Crash + LOOK 1.6.13

Tiny wrapper-hardening release.

`lmv a.txt b.txt ../dst/` and `lcp a.txt b.txt ../dst/` now explicitly treat the final argument as the destination by popping it from the source array before invoking LOOK's existing batch engine.

LOOK is 3.10.2. Future Crash remains 1.1.7.


---

<!-- source: RELEASE-1.6.14.md -->

# Future Crash + LOOK 1.6.14

This release closes a reliability gap between *talking about* host operations and actually performing them.

When the operator explicitly asks LO to create, write, copy, move, rename, edit, or remove local files, LOOK now requires a filesystem mutation tool call before a success report is accepted. A prose-only completion gets one silent retry with a tool-required instruction. If the model still fails to execute a tool, LOOK reports that no filesystem mutation occurred.

Workspace also gains read-only process, listening-port, and compact system inspection tools. Arbitrary command execution remains reserved for Power/Unsafe.

LOOK is 3.10.3. Future Crash remains 1.1.7.


---

<!-- source: RELEASE-1.6.15.md -->

# Future Crash + LOOK 1.6.15

LOOK's interactive filer can now hand its selected working set directly to LO.

Filter/select normally, mark paths with `Tab` or `A`, then press **`L`**. If nothing is marked, the highlighted path is handed off. LO opens with an explicit path manifest and reports the count in its startup banner.

The handoff does not preload file contents. LO uses its existing bounded file tools only when needed. Its workspace is rooted at the nearest common selected directory so every handed-off path remains inside the accessible tool boundary.

LOOK is 3.10.4. Future Crash remains 1.1.7.


---

<!-- source: RELEASE-1.6.16.md -->

# Future Crash + LOOK 1.6.16

Tiny filer-input cleanup.

The interactive filer now has one simple vertical navigation grammar: `j/k` (or `J/K`) and the arrow keys. The accidental `J/K/L/;` directional scheme is gone.

`L` is therefore unambiguous and always means: hand the highlighted or marked paths to a new LO session as context.

LOOK is 3.10.5. Future Crash remains 1.1.7.


---

<!-- source: RELEASE-1.7.0.md -->

# Future Crash + LOOK 1.7.0

LOOK's filer finally has direct parent navigation.

In the ordinary browse state, press **`>`** (Shift-.) to move up one filesystem directory, exactly like `..`, without exiting the interface. Escape remains history/back navigation, so the two behaviors are no longer conflated.

When actively typing a filter, `>` is still just a searchable character.

LOOK is 3.11.0. Future Crash remains 1.1.7.


---

<!-- source: RELEASE-1.8.0.md -->

# Future Crash + LOOK 1.8.0

The filer now has a persistent cross-directory working set.

Mark paths with `Tab` or `A`, navigate with Enter and `<` (Shift-,), and continue selecting elsewhere. The set survives navigation. `C`, `M`, `R`, `Y`, clipboard actions, and `L` operate on the accumulated set; `X` clears it.

The status line is intentionally informative:

- `SELECTED · 3` — all three selected items are in the current view.
- `SELECTED · 7 / 3 HERE` — seven total selected paths, three in the current directory/view.

The local-only state is green; the cross-directory state uses an amber/yellow accent so an off-screen working set is difficult to forget.

Directories are stored as paths, not recursively expanded selections.

LOOK is 3.12.0. Future Crash remains 1.1.7.


---

<!-- source: RELEASE-1.8.1.md -->

# Future Crash + LOOK 1.8.1

Small filter-input correction.

While typing a filter, lowercase `j` and `k` are ordinary searchable characters. Use Shift-J / Shift-K (`J/K`) or ↑/↓ to move through matches. In ordinary browse/select mode, lowercase `j/k` continue to navigate normally.

LOOK is 3.12.1. Future Crash remains 1.1.7.


---

<!-- source: RELEASE-1.9.0.md -->

# Future Crash + LOOK 1.9.0

This release tightens four interaction layers at once.

1. **Path completion everywhere:** filer copy/move destinations now complete paths with Tab, and shell file-action helpers use repeated native path completion for every operand.
2. **LOOK-native global find:** `f` and `fznv` keep their fast global retrieval behavior but use LOOK's own visual/action language.
3. **Temporal memory:** recent exchanges and semantic candidates carry age, creation, and reinforcement information. Memory is explicitly historical context, never a pending task queue.
4. **Background LO message passing:** `lo bg REQUEST` queues one-shot LO work. Jobs emit durable completion/failure events, which the shell surfaces at the next prompt. `lk jobs` and `lk events` expose the state.

The background layer is deliberately queue/event based rather than a resident daemon. It establishes a stable local messaging contract that Future Crash, the shell, or a future Unix-socket/HTTP broker can all use.

LOOK is 3.13.0. Future Crash remains 1.1.7.


---

<!-- source: RELEASE-1.9.1.md -->

# Future Crash + LOOK 1.9.1

This release fixes a real transaction bug in multi-file copy/move.

LOOK's undo history is capped at 20 public records. Earlier batch code inferred newly-created undo entries by comparing the history length before and after the operation. Once the history was already full, its length stayed 20, so successful multi-file moves could be falsely reported as `undo journal mismatch`.

Batch operations now carry an explicit transaction ID. Temporary item records are allowed to exceed the public history cap until the operation commits; they are then collapsed into one batch undo record. This also makes batches larger than 20 items safe.

Success receipts identify what moved. Failure receipts identify the source that failed and report rollback status.

Interactive file prompts also retain Tab completion while giving bare Escape an explicit cancel binding.

LOOK is 3.13.1. Future Crash remains 1.1.7.


---

<!-- source: RELEASE-1.9.3.md -->

# Future Crash + LOOK 1.9.3

Global find is responsive again.

The 1.9.0 LOOK-native global finder built the complete home-directory catalog before entering its interactive filter, which introduced a visible multi-second dead period on larger homes.

`f` and `fznv` now return to the better streaming architecture: `fd` (or portable `find`) produces paths continuously while fzf is already accepting input. The finder is styled to LOOK's visual language and exposes fzf's live spinner/match information during enumeration.

`f` hands the chosen result into LOOK for the normal preview/action workflow. `fznv` opens it directly in Neovim.

LOOK is 3.13.3. Future Crash remains 1.1.7.


---

<!-- source: RELEASE-2.0.0.md -->

# Future Crash + LOOK 2.0.0

## Portable identity

2.0 separates LOOK into four state layers: program, profile, machine, and runtime.

The **profile** is the portable part of the evolving local AI: memory, recent conversational continuity, core customization, skills, personalities, access/personality/thinking preferences, preferred model name, and feedback settings.

Use:

```text
lk profile
lk profile backup ~/Documents/LOOK
lk profile export
lk profile restore look-profile-YYYYMMDD-HHMMSS.zip
```

A backup destination is remembered. Backups are timestamped snapshots with configurable retention. Export creates a single migration ZIP. Restore validates schema and paths, then creates a local safety snapshot before replacing the portable live state.

Secrets, undo/trash, jobs/events, memory queues/locks, PIDs, generated caches, and machine-specific Ollama host configuration do not travel.

## Skills promotion

`lk skills export` writes only locally learned skills. That file can be reviewed and deliberately folded into a future built-in skills pack without treating a personal profile as distribution source code.

## Terminal expression

`lk feedback` controls the shared finite feedback layer.

```text
lk feedback
lk feedback motion off|subtle|normal
lk feedback sound on|off
lk sound
lk feedback demo
```

Sound defaults off. Motion defaults subtle. Feedback is disabled automatically when stdout is not a TTY.

LOOK is 4.0.0. Future Crash remains 1.1.7.


---

<!-- source: RELEASE-2.0.1.md -->

# Future Crash + LOOK 2.0.1

A surgical information-trust pass on 2.0.

LO now has named canonical edges for WEATHER, PLACE, WIKI, DATA, PAPERS, and ARCHIVE, with WEB as the general fallback. Canonical results carry source, retrieval time, source time where available, and a provenance class.

The release also adds `LIVING-WITH-LOOK.md`: a narrative explanation of how the system is meant to be used day to day rather than another command glossary.

LOOK is 4.0.1. Future Crash remains 1.1.7.


---

<!-- source: RELEASE-2.0.2.md -->

# Future Crash + LOOK 2.0.2

LO had become more capable than its original runtime ceilings allowed. Complex but ordinary tasks could consume most of a 1,400–2,000-token generation budget in reasoning/tool work and reach the answer only on a follow-up turn.

2.0.2 makes runtime capacity adaptive:

| Tier | Context | Output ceiling | Tool rounds |
|---|---:|---:|---:|
| FAST | 8,192 | 1,500 | 4 |
| STANDARD | 16,384 | 3,500 | 8 |
| DEEP | 24,576 | 6,000 | 12 |

These are ceilings, not quotas. A weather lookup or short file action still stops as soon as it is done.

STANDARD is intended for tasks such as counting files, inspecting a directory, comparing several selected files, explaining code, or searching a workspace. DEEP is selected for larger multi-file analysis, debugging, architecture/refactoring work, or explicit deep-thinking mode.

Use `lk budget <example request>` to inspect which tier LOOK would choose while benchmarking different local models.

LOOK is 4.0.2. Future Crash remains 1.1.7.


---

<!-- source: RELEASE-2.0.3.md -->

# Future Crash + LOOK 2.0.3

## Deterministic directory inspection

LO no longer needs to list a directory into context and count entries itself.

The read-only `inspect_directory` tool returns exact, bounded statistics:

```text
path
recursive
files
directories
symlinks
other
total_entries
file_bytes
scanned_entries
truncated
limit
elapsed_ms
```

LO is instructed to prefer this tool for exact file/folder counts and directory-stat questions.

## Natural feedback as weak supervision

Ordinary conversation can now help LO improve without a special training UI.

Clear feedback such as “great job,” “that worked,” “that didn’t work,” or “you made that up” triggers a detached background review of the immediately preceding interaction.

The reviewer may produce exactly one result:

- `NONE` — nothing reusable was learned.
- `NEW` — a new generalized operational skill.
- `REINFORCE` — an existing learned skill clearly contributed to success.
- `WEAKEN` — an existing skill clearly contributed to failure.
- `CORRECT` — a reusable corrective lesson.

Praise/criticism itself is never stored as a skill.

`skills.md` remains readable/editable. Reinforcement state is stored in `skill_state.json`, which travels with the portable profile.

Use:

```text
lk skills state
```

to inspect confidence and positive/negative hits.

LOOK is 4.0.3. Future Crash remains 1.1.7.


---

<!-- source: RELEASE-2.1.0.md -->

# Future Crash + LOOK 2.1.0 — Living AI

LOOK now has a resident local AI coordinator rather than a collection of unrelated one-shot workers.

```text
shell / LOOK / Future Crash / LO
              │
              ▼
       ~/.local/share/look/ai.sock
              │
              ▼
          look_ai.py
      P0 foreground lease
      P1 explicit background jobs
      P2 memory + skill maintenance
              │
              ▼
            Ollama
       local or remote 3090
```

The socket is intentionally only the fast coordination path. Jobs, memory work, skill feedback, and events remain durable files, so pending work survives broker crashes/restarts.

## Living Memory

Recent conversation remains literal continuity and stores both sides of an exchange. Semantic candidates now reinforce by meaning rather than exact wording. Forgetting is based on elapsed time rather than chat volume. Repeated/durable evidence triggers long-term rewriting immediately; candidates represented in long-term leave the active pool.

Background cognition stops when there is no new evidence. LOOK never repeatedly rewrites memory merely because the GPU is idle.

## Control

```text
lk ai
lk ai start
lk ai stop
lk ai wake
```

LOOK is 4.1.0. Future Crash remains 1.1.7.

## Failure behavior

The broker does not equate “the model call failed softly” with “memory work completed.” It proves the configured Ollama endpoint is reachable before consuming a durable memory job. Failed housekeeping remains queued, records the worker error, and uses retry backoff.


---

<!-- source: RELEASE-2.1.1.md -->

# Future Crash + LOOK 2.1.1 — Living AI release hardening

2.1.1 is the distribution-ready maintenance release of Living AI.

The only runtime behavior change from 2.1.0 is status semantics: `lk ai status` now returns success when it correctly reports either a running or stopped broker. A stopped broker is a valid inspected state, not a command failure.

This release also synchronizes version metadata across README, installer, LOOK runtime, and release documentation and revalidates the broker/memory package for deployment across multiple machines.

Versions:

- Future Crash + LOOK: 2.1.1
- LOOK: 4.1.1
- Future Crash: 1.1.7


---

<!-- source: RELEASE-2.1.2.md -->

# Future Crash + LOOK 2.1.2 — Shared inference lane

Versions:

- Future Crash + LOOK: 2.1.2
- LOOK: 4.1.2
- Future Crash: 1.1.8

## Purpose

2.1.2 coordinates model use without merging AI identities.

LO and Future Crash still have different system instructions, memories, personalities, permissions, and tools. Living AI now acts as the shared inference traffic coordinator underneath them.

## Priority contract

1. Explicit interactive work may start immediately.
2. Living AI will not start maintenance while an interactive Future Crash lease is active.
3. Automatic Future Crash ambient work only starts when:
   - no interactive lease is active,
   - Living AI is not already processing a background unit,
   - no queued LO background job, memory job, or skill-reflection job is waiting.
4. Once a scheduled Future Crash Thread begins, its repair/continuation passes may finish as the same admitted unit of work.

## Standalone behavior

Future Crash does not require LOOK or Living AI. If the broker socket is unavailable, its Oracle behaves exactly as before.

## Boundary

Coordination is resource scheduling only. It does not share:

- personality
- conversation memory
- long-term memory
- learned skills
- host permissions
- access profiles
- tool state


---

<!-- source: RELEASE-2.1.3.md -->

# Future Crash + LOOK 2.1.3 — Living Memory observability

Versions:

- Future Crash + LOOK: 2.1.3
- LOOK: 4.1.3
- Future Crash: 1.1.8

## Why

A healthy Living AI broker could drain the memory queue while candidate memory appeared frozen. The reason was subtle: RECENT is committed directly, but semantic memory depends on a background extractor. If that extractor repeatedly returned `NONE`, the queue correctly returned to zero while no new candidate evidence appeared.

2.1.3 makes that state visible and less brittle.

## Evidence paths

Memory extraction now runs in this order:

1. model semantic extraction;
2. deterministic obvious-evidence fallback for clearly stated preferences, durable project state, conventions, and explicit memory language;
3. explicit-memory fallback.

The deterministic path is deliberately conservative. It does not try to infer personality or facts from ordinary chatter.

## Diagnostics

`lk memory` now reports:

```text
extraction · candidate:model just now · 4/9 candidate · 5 none
```

or:

```text
extraction · none 2 minutes ago · 4/10 candidate · 6 none
```

This separates three conditions that previously looked identical:

- exchange was never processed;
- exchange was processed and judged non-memory;
- exchange produced candidate evidence.

Any recorded worker error is also shown directly.


---

<!-- source: RELEASE-2.1.4.md -->

# Future Crash + LOOK 2.1.4 — Living Memory reinforcement correctness

Versions:

- Future Crash + LOOK: 2.1.4
- LOOK: 4.1.4
- Future Crash: 1.1.8

This release fixes candidate reinforcement without changing the broker or scheduler.

The regression case is Sapphire:

```text
We're using sapphire as the codename for the current LOOK memory test.
We decided sapphire will remain the codename for this current LOOK memory test.
We're continuing to use sapphire as the LOOK memory-test codename.
```

Expected lifecycle:

```text
first evidence  → candidate / USES 1
second evidence → same candidate / USES 2 / importance +8
third evidence  → same candidate / USES 3 / promotion
                → LONG-TERM
                → active Sapphire candidate retired
```

If the model extractor returns NONE on a later paraphrase, a strong distinctive-token overlap with an existing active candidate may still count as reinforcement.

`lk memory` now persists cumulative extraction and consolidation receipts.


---

<!-- source: RELEASE-2.1.5.md -->

# Future Crash + LOOK 2.1.5 — Living AI version handshake

Versions:

- Future Crash + LOOK: 2.1.5
- LOOK: 4.1.5
- Future Crash: 1.1.8

## Bug

Living AI is a resident process and imports LOOK once when it starts.

Previously, installing a newer LOOK version updated files on disk but did not invalidate an already-running broker. That broker could continue processing new memory jobs with old extraction/reinforcement code. The queue would drain normally, making the stale runtime difficult to detect.

## Fix

Broker status now returns the imported LOOK core version. Before LOOK wakes background work, it compares:

```text
running broker core
vs
installed LOOK VERSION
```

If they differ, LOOK stops the old broker, launches the installed broker, verifies the new version, and only then wakes background work.

`lk ai status` now includes:

```text
core        4.1.5
```

A legacy/stale broker is explicitly visible rather than silently trusted.


---

<!-- source: RELEASE-2.1.6.md -->

# Future Crash + LOOK 2.1.6 — Living AI liveness hardening

Versions:

- Future Crash + LOOK: 2.1.6
- LOOK: 4.1.6
- Future Crash: 1.1.8

This release does not change memory semantics. It hardens the resident Living AI process.

A PID file is no longer accepted as proof that a broker exists. The broker's Unix socket must answer the status protocol. This prevents stale PID files or OS PID reuse from leaving durable work queued behind a nonexistent coordinator.

The broker also contains unexpected background exceptions rather than exiting, and records them in:

```text
~/.local/share/look/ai_errors.log
```

Finally, `lk memory` treats:

```text
memory queue > 0
living AI stopped
```

as a recoverable condition and attempts to start/wake processing immediately.


---

<!-- source: RELEASE-2.1.7.md -->

# Future Crash + LOOK 2.1.7 — Input polish + AI performance telemetry

Versions:

- Future Crash + LOOK: 2.1.7
- LOOK: 4.1.7
- Future Crash: 1.1.8

## Filer

- `Tab` and `Shift-Tab` both toggle the highlighted mark.
- `←` goes to the parent directory wherever parent navigation is available.
- `→` follows the same inward/open behavior as Enter.
- Footer wording distinguishes `B clipboard`, `C Copy To`, and `M Move To`.

## Waiting feedback

LOOK's four-frame activity indicator now appears for operations where the user is genuinely waiting: first model response, blocking filesystem mutations, explicit command execution, and global file catalog scans. Background memory/skill work remains non-blocking and therefore reports receipts rather than spinners.

## AI performance

`lk ai stats` stores a rolling 100-request telemetry window without prompt/response content.

Per task:

- wall time
- inference rounds
- tool calls
- prompt token count and prompt-eval time/rate
- generated token count and generation time/rate
- model load duration

Live Ollama status adds model VRAM allocation and context length from `/api/ps`. A local NVIDIA host also adds `nvidia-smi` memory/utilization/temperature detail. Remote hosts are never mislabeled with the local machine's GPU statistics.


---

<!-- source: RELEASE-2.1.8.md -->

# Future Crash + LOOK 2.1.8 — Warm model residency

Versions:

- Future Crash + LOOK: 2.1.8
- LOOK: 4.1.8
- Future Crash: 1.1.8

LO now sends `keep_alive=-1` on normal interactive Ollama chat requests.

This targets the measured failure mode where a Qwen 30B task spent more than half its wall time reloading ~19 GB of model weights before doing useful work.

`lk ai stats` classifies tasks as:

- **cold** when cumulative Ollama load duration is at least 1 second
- **warm** otherwise

For remote Ollama hosts, `/api/ps` exposes model residency, not physical GPU capacity. The stats surface now labels these fields correctly as `GPU resident` and `model size`.


---

<!-- source: RELEASE-2.1.9.md -->

# Future Crash + LOOK 2.1.9 — Ollama keep-alive compatibility

Versions:

- Future Crash + LOOK: 2.1.9
- LOOK: 4.1.9
- Future Crash: 1.1.8

2.1.8 introduced permanent model residency but encoded the value as a JSON string:

```json
"keep_alive": "-1"
```

Some Ollama builds reject that request with HTTP 400.

2.1.9 sends the API's numeric permanent-residency value:

```json
"keep_alive": -1
```

Everything else from 2.1.8 is unchanged.


---

<!-- source: RELEASE-2.1.10.md -->

# Future Crash + LOOK 2.1.10 — File destination fidelity

Versions:

- Future Crash + LOOK: 2.1.10
- LOOK: 4.1.10
- Future Crash: 1.1.8

## Fixed

`copy_path` and `move_path` referenced a missing `_final_destination` helper. A move attempt could therefore crash the entire LO process with `NameError`. The helper is restored through LOOK's canonical destination planner and filesystem tool exceptions are contained at the tool boundary.

## Destination contract

If the user names a destination folder, the tool path must preserve it.

From workspace `~`:

```text
make boilerplate3.html in Downloads
→ Downloads/boilerplate3.html
```

If `~/Downloads` is outside the current WORKSPACE boundary, LO reports that boundary instead of silently creating `./boilerplate3.html`.

## Reveal

LO has a read-only `reveal_path` tool for “show me the file” requests.

Direct command:

```text
lk reveal PATH
```

macOS uses Finder reveal. Linux opens the containing folder through `xdg-open`. Windows uses Explorer/select where available.

## Shell navigation

The packaged Zsh profile no longer aliases `cd` to zoxide.

```text
cd  → real builtin cd, with Zsh correction suppressed
z   → zoxide fuzzy/history navigation
```

This ensures a newly downloaded/extracted directory can always be entered by exact path before zoxide has learned it.


---

<!-- source: RELEASE-2.2.0.md -->

# Future Crash + LOOK 2.2.0

Versions:

- Future Crash + LOOK: 2.2.0
- LOOK: 4.2.0
- Future Crash: 1.1.9

## Terminal ownership

The terminal/tab title is now a lightweight owner indicator:

```text
● LOOK
● LO
● FUTURE CRASH
```

When control returns to Zsh, the title becomes:

```text
LOOK · <current-folder>
```

The indicator uses standard OSC title escapes and does not alter prompt content.

## Undo history

`lk undo` remains strict: only the newest transaction may be reversed, and divergence causes a refusal.

New commands:

```text
lk undo list
lk undo skip
```

`lk undo list` classifies active records as READY or BLOCKED and explains why.

`lk undo skip` is intentionally conservative:
- only the newest record may be skipped;
- it must already be BLOCKED;
- skipping changes only undo history, never the filesystem;
- the skipped record is retained in a small diagnostic history.

This lets the user explicitly abandon a divergent transaction and reach older undo history without LOOK guessing.

## File execution correctness

A failed mutation tool receipt can no longer be followed by a prose success claim. If a requested filesystem mutation has no successful receipt, LO reports the failure.

Common home-folder names in creation requests are normalized:

```text
"make x.html in the Downloads folder"
→ ~/Downloads/x.html
```

If that canonical destination lies outside the starting WORKSPACE boundary, the operation is refused cleanly instead of silently creating the file in the current directory.


---

<!-- source: RELEASE-2.2.1.md -->

# Future Crash + LOOK 2.2.1

Versions:

- Future Crash + LOOK: 2.2.1
- LOOK: 4.2.1
- Future Crash: 1.1.9

## Workspace is now a default trust boundary

LO can request a path outside the folder where the session started. LOOK resolves the exact requested path first, then enforces access locally.

When access is missing:

```text
LO FILE ACCESS
  wants WRITE  ~/Downloads/example.html
  workspace    ~/Projects/current
  grant root   ~/Downloads

[A] once · [S] session · [P] always · [H] personal folders · Enter/Esc cancel
```

The model does not decide permission and cannot turn a denial into a different destination.

### Grant scopes

- **Once** — the complete current filesystem tool transaction only.
- **Session** — the granted directory for this LO process.
- **Always** — persistent local grant.
- **Personal** — persistent read/write access to existing `~/Desktop`, `~/Documents`, and `~/Downloads`.

Write grants imply read access. Read-only grants can be created explicitly.

### Management

```text
lk access
lk access personal
lk access add ~/SomeFolder write
lk access add ~/Reference read
lk access remove ~/SomeFolder
lk access clear
```

Persistent rules live in LOOK's private state directory and are written mode 0600.

### Safety invariants

- The current workspace remains trusted by default.
- Missing grants in background/noninteractive jobs fail closed.
- Cancel means no filesystem mutation.
- Destination denial never falls back to the current directory.
- Existing remove confirmation and undo journaling remain intact.


---

<!-- source: RELEASE-2.2.2.md -->

# Future Crash + LOOK 2.2.2

Versions:

- Future Crash + LOOK: 2.2.2
- LOOK: 4.2.2
- Future Crash: 1.1.9

## Fix

Older LOOK releases installed aliases such as `lo`, `fc`, and `rst`. Newer releases use functions so they can manage terminal ownership titles and cleanup.

On `rb` / `exec zsh`, Zsh could still have the old aliases active while sourcing the new profile. Zsh performs alias expansion during parsing, producing errors such as:

```text
defining function based on alias `lk'
parse error near `()'
```

The LOOK profile now executes:

```zsh
unalias lk lo fc rst commands 2>/dev/null
```

before any same-name function definitions in the reload section.

No other behavior changes.


---

<!-- source: RELEASE-2.2.3.md -->

# Future Crash + LOOK 2.2.3

Versions:

- Future Crash + LOOK: 2.2.3
- LOOK: 4.2.3
- Future Crash: 1.1.10

## Receipts are reality

Successful filesystem receipts now carry canonical absolute paths.

```text
CREATE FILES OK · 1 files
  /Users/name/Downloads/test-boilerplate.html
  undo available · lk undo
```

and:

```text
WRITE OK · /Users/name/Downloads/file.html · 123 bytes
```

The model is instructed that these receipts are authoritative. Prior conversation, recent memory, or assumptions about the current directory must never override them.

## Mutation-request classification

The host's anti-hallucination guard now distinguishes:

```text
make a file in Downloads        → execution request
could you move this file        → execution request

did you make the file?          → discussion/question
where did you make it?          → discussion/question
you did make it correctly       → retrospective
good job making that file       → feedback
```

This prevents successful earlier work from being contradicted on the next conversational turn.

## Terminal ownership

Terminal/tab state now distinguishes all four situations:

```text
● LOOK
● LO
● FUTURE CRASH
◌ FUTURE CRASH · SHELL · <folder>
```

The last state means Future Crash is still running as the parent, but you are temporarily using its child shell. Exiting that shell restores `● FUTURE CRASH`.


---

<!-- source: RELEASE-2.3.0.md -->

# Future Crash + LOOK 2.3.0 — Living Memory compiler

Versions:

- Future Crash + LOOK: 2.3.0
- LOOK: 4.3.0
- Future Crash: 1.1.10

## Mental model

Living Memory is no longer one summary plus a small frozen candidate list.

```text
conversation
    ↓
candidate evidence
    ↓
reinforcement / contradiction / decay / competition
    ↓
durable atomic memories
    ↓
domain summaries
    ↓
tiny core routing summary
    ↓
relevant retrieval into the current prompt
```

Candidates are intentionally cheap hypotheses. Long-term durable memory is harder to earn.

## Domains

Durable atoms are classified into:

- PERSONAL — interests, favorites, tastes
- PREFERENCES — reusable choices and conventions
- PROJECTS — durable project decisions/context
- STYLE — interaction and working-style preferences
- GENERAL — useful durable facts that do not fit another domain

Machine/runtime facts such as the current GPU, current LOOK version, current Ollama endpoint, cwd, or current host belong to deterministic system state and are excluded from autobiographical memory.

## Context budget

The on-disk durable store may contain up to 240 atomic memories without putting them all in the prompt.

Normal retrieval injects only:

- one compact core summary;
- up to two relevant domain summaries;
- up to six relevant durable atoms;
- up to four relevant candidate memories.

This makes storage generous while attention remains intentionally small.

## Background compiler

The resident Living AI broker may use otherwise-idle cycles to recompile memory no more than once every six hours.

The compiler is instructed to:

- preserve meaning while reducing tokens;
- merge redundancy aggressively;
- never broaden scope;
- preserve qualifiers and uncertainty;
- never invent causality or preference;
- remove machine/runtime facts from user memory.

Promotion triggers an immediate compile. Durable reinforcement can also invalidate summaries for recompilation.

Manual command:

```text
lk memory compact
```

## Migration

Schema-2 long-term summary prose is preserved as:

```text
LEGACY (inactive)
```

It remains inspectable but is not injected into LO context automatically. This avoids carrying forward old over-generalized wording such as converting a project-scoped preference into a universal preference.

## Diagnostics

`lk memory` now shows:

- core summary;
- compiled durable domains;
- top durable atoms;
- recent conversation;
- active candidates;
- extraction ratio;
- promotions;
- consolidations;
- candidate evictions;
- compiler age;
- background queue/broker state.

## Documentation audit

`lk help all`, `lk commands`, `lk settings`, and Zsh completion now reflect:

- access grants;
- undo list/skip;
- reveal;
- AI stats;
- thinking vs think-display;
- current filer arrows/Shift-Tab;
- terminal ownership states;
- Living Memory compiler commands and concepts.


---

<!-- source: RELEASE-2.3.1.md -->

# Future Crash + LOOK 2.3.1

Versions:

- Future Crash + LOOK: 2.3.1
- LOOK: 4.3.1
- Future Crash: 1.1.10

## Fix

LOOK 4.3.0 made long-term memory retrieval query-aware, but the initial message setup attempted:

```text
_memory_context(memory, prompt)
```

before `prompt` had been assigned.

4.3.1 uses a stable memory system-message slot. For every user turn:

```text
read current prompt
→ reload latest memory
→ retrieve relevant memory for this prompt
→ replace memory slot
→ run inference
```

This preserves query-aware retrieval without carrying obsolete memory snapshots forward in the conversation.


---

<!-- source: RELEASE-2.3.2.md -->

# Future Crash + LOOK 2.3.2 — Native command authority

Versions:

- Future Crash + LOOK: 2.3.2
- LOOK: 4.3.2
- Future Crash: 1.1.10

## POWER command execution

Models no longer negotiate command permission in conversation.

The model proposes `run_command`. LOOK then owns the policy and any user interaction.

Known read-only inspections run immediately:

```text
ollama --version
git --version
python3 --version
ollama list
ollama ps
git status
nvidia-smi
pwd
whoami
uname ...
```

Unknown or potentially mutating commands use the native prompt:

```text
command › brew upgrade ollama
[y] once · [s] allow command this session · Enter/Esc cancel ›
```

A session grant applies only to that exact normalized command.

Shell composition, redirection, and destructive forms are never classified as safe inspection merely because they contain flags.

## No terminal-input competition

`run_command` subprocesses receive DEVNULL stdin. A background command therefore cannot accidentally steal input from LO's conversational terminal and appear to hang while waiting for input.

## Agent execution repair

Some models can identify the right command in reasoning but emit prose such as:

```text
I cannot check that here. Run `ollama --version`.
```

In POWER/UNSAFE, LOOK recognizes only a known-safe inspection in that situation, executes it once at the host layer, feeds the receipt back to the model, and asks for the final answer.

This is deliberately narrow. Unknown or mutating commands are never auto-extracted from prose.

## Thinking renderer

Compact thinking previously contained double-escaped terminal sequences:

```text
\r\033[2K
```

They are now actual control characters, restoring the intended rolling three-line compact display across Qwen and GPT-OSS-style thinking streams.

## Zsh natural language

`lo` is now wrapped with Zsh `nocorrect`, so prompts such as:

```text
lo what version ollama are we running
```

are passed to LO verbatim instead of prompting to replace `version` with a local `VERSION` filename.

## Model benchmark

`lk ollama test` now separates:

- **TOOLS** — controlled tool-schema judgment (3 tests)
- **AGENT** — whether a natural inspection request actually produces the appropriate tool call
- **EXACT** — deterministic response test
- TTFT / generation rate / declared capabilities

This prevents a 3/3 tool score from hiding an agent-execution weakness.


---

<!-- source: RELEASE-2.3.3.md -->

# Future Crash + LOOK 2.3.3 — Desktop bridge + agent cleanup

Versions:

- Future Crash + LOOK: 2.3.3
- LOOK: 4.3.3
- Future Crash: 1.1.10

## Agent-loop cleanup

LOOK now distinguishes model capability from host capability.

If Ollama reports that a selected model does not support tools, LOOK does not send tool schemas to that model. This avoids HTTP 400 failures while keeping ordinary chat/thinking available.

POWER/UNSAFE still retain LOOK's narrow host-side safe-inspection repair. When that repair runs, the following model pass is explicitly final-answer-only and receives no tools, preventing redundant inspection loops.

## Compact thinking

The three-line compact thinking renderer now redraws exactly the previous number of lines and clips content to terminal width. This fixes duplicated or concatenated thinking fragments after the rolling window reaches full height.

## Desktop bridge

The terminal is the control surface, not the boundary of the computer.

Direct commands:

```text
lk open PATH
lk preview PATH
lk reveal PATH
lk apps
```

LO tools:

```text
open_path
preview_path
reveal_path
```

Semantics:

- **open** — launch the artifact in a graphical/default/preferred application.
- **preview** — quick external preview; macOS prefers Quick Look.
- **reveal** — locate the path in Finder/file manager.

### App preferences

Categories:

```text
browser
editor
image
pdf
video
audio
```

Examples:

```text
lk apps video vlc
lk apps video mpv
lk apps pdf system
lk apps editor code
```

`system` is the default for every category.

On macOS, custom application names are passed through `open -a`. On Linux, preferred executable names are resolved from PATH; otherwise `xdg-open` handles the system default. Windows uses its file associations when no override is configured.

No additional GUI application is mandatory. LOOK Doctor reports available system openers, Quick Look, terminal preview helpers, and detected VLC/mpv installations.

### Permission boundary

When LO opens/previews/reveals a path, normal LOOK read/path-grant rules still apply. A direct `lk open PATH` is an explicit user command and uses that path directly.


---

<!-- source: RELEASE-2.3.4.md -->

# Future Crash + LOOK 2.3.4

Versions:

- Future Crash + LOOK: 2.3.4
- LOOK: 4.3.4
- Future Crash: 1.1.10

## Fix

`lk ollama test` previously used the generic resident-model chooser. If `qwen3:30b` was already resident, selecting `deepseek-r1:32b` or `qwen3:8b` in `lk ollama models` could still benchmark `qwen3:30b`.

Single-model testing now means exactly:

```text
LOOK-selected model
→ verify installed on active host
→ benchmark that model
```

Resident state affects warm/cold timing, but no longer changes which model is tested.

`lk ollama test --all` continues to test all enabled installed models.


---

<!-- source: RELEASE-2.3.5.md -->

# Future Crash + LOOK 2.3.5

Versions:

- Future Crash + LOOK: 2.3.5
- LOOK: 4.3.5
- Future Crash: 1.1.10

## Fix

Zsh already owns the command name `fc` for history management.

Older LOOK releases also used `fc` as a Future Crash shortcut. Shell/history tooling can legitimately execute commands such as:

```text
fc -p -a /dev/null 0 0
```

Because LOOK had replaced the builtin with a function, those history arguments were forwarded to Future Crash and appeared as:

```text
future_crash.py: error: unrecognized arguments: -p -a /dev/null 0 0
```

Pasting text could trigger history machinery, making the error look paste-related.

## Resolution

LOOK no longer defines `fc`.

On reload it explicitly removes any stale LOOK `fc` function:

```zsh
unalias fc 2>/dev/null
unfunction fc 2>/dev/null
```

which exposes Zsh's native builtin again.

Future Crash launchers are now:

```text
future-crash
rst
fcr
```

`fcr` replaces the old short `fc` alias/function.

Future Crash remains strict about unknown command-line arguments.


---

<!-- source: RELEASE-2.3.6.md -->

# Future Crash + LOOK 2.3.6

Versions:

- Future Crash + LOOK: 2.3.6
- LOOK: 4.3.6
- Future Crash: 1.1.10

`fc` is now a compatibility dispatcher:

```zsh
fc() {
  if (( $# == 0 )); then
    _future_crash_owned
  else
    builtin fc "$@"
  fi
}
```

This preserves both behaviors:

```text
fc
→ launch Future Crash

fc -p -a /dev/null 0 0
→ native Zsh history builtin
```

So normal paste/history machinery cannot accidentally launch Future Crash, while the short launcher remains available.


---

<!-- source: RELEASE-2.3.7.md -->

# Future Crash + LOOK 2.3.7

Versions:

- Future Crash + LOOK: 2.3.7
- LOOK: 4.3.7
- Future Crash: 1.1.10

## `fc` is reserved for Zsh

LOOK no longer attempts to overload `fc`.

In Zsh, `fc` is the native history editor/manager. Shell plugins and paste/history machinery may call it with arguments. Bare `fc` can legitimately open the configured history editor.

Future Crash launchers are now:

```text
fcr
rst
future-crash
```

On shell reload, LOOK removes any stale `fc` function left by older releases and does not redefine it.


---

<!-- source: RELEASE-2.3.8.md -->

# Future Crash + LOOK 2.3.8 — Polite shell namespace

Versions:

- Future Crash + LOOK: 2.3.8
- LOOK: 4.3.8
- Future Crash: 1.1.10

## Three layers

### Canonical

```text
lk
lk detail
lk dirs
lk files
lk tree
lk recent
lk size
```

### Fast LOOK namespace

Always installed:

```text
lkl  detail
lkd  directories
lkf  files
lkt  tree
lkr  recent
lkz  size
```

These names deliberately carry the `lk` prefix and are treated as LOOK-owned vocabulary.

### Ultra-short convenience layer

```text
l
ll
ld
lf
lt
lr
lz
```

These are optional shell conveniences.

Default policy is `polite`: if a name already belongs to an alias, function, builtin, or executable, LOOK leaves it alone.

```text
lk shortcuts
lk shortcuts polite
lk shortcuts force
rb
```

`force` may replace an alias or function. It still does not replace a shell builtin or executable on PATH.

This means `/usr/bin/ld`, native `ls`, an installed `lf` file manager, and similar established commands remain reachable normally.

## Retired global aliases

LOOK no longer installs:

```text
lsd
lsf
lc
```

`lsd` in particular is an established modern `ls` replacement.

## Principle

LOOK owns one broad namespace: `lk`.

Fast aliases are conveniences, not prerequisites. Every filesystem view remains available under `lk ...` even when a short alias is unavailable because the user's shell already owns that name.


---

<!-- source: RELEASE-2.3.9.md -->

# Future Crash + LOOK 2.3.9

Versions:

- Future Crash + LOOK: 2.3.9
- LOOK: 4.3.9
- Future Crash: 1.1.10

## Model benchmark runtime fit

`lk ollama test` now separates two questions:

1. Can the model do LOOK work correctly?
2. Is it responsive enough to be pleasant interactively?

The table adds a runtime `FIT` column:

```text
EXCELLENT
GOOD
SLOW
POOR
```

The classification uses intentionally broad warm TTFT and generation-rate thresholds. It is a user-experience signal, not a hardware diagnosis.

A model with excellent tools/agent/exact results but pathological latency is therefore reported honestly, for example:

```text
gemma4:31b   42.53s   14.9   POOR   3/3   yes   yes
runtime note · capability may be excellent; runtime is pathological · inspect `lk ai stats` / `ollama ps`
```

Use `lk ai stats` for LOOK/Ollama telemetry and `ollama ps` for Ollama's current model residency/processor information.

The 2.3.8 shell namespace remains unchanged: canonical `lk ...`, permanent `lk*` fast commands, collision-aware optional short aliases, and native `fc`/`ls`/system executables left alone.


---

<!-- source: RELEASE-2.4.0.md -->

# Future Crash + LOOK 2.4.0 — Settings control room

Versions:

- Future Crash + LOOK: 2.4.0
- LOOK: 4.4.0
- Future Crash: 1.1.10

## A human-facing settings surface

LOOK now has one obvious answer to:

> Where do I change that?

```text
lk settings
```

The control room is searchable. Typing narrows all settings immediately, including by plain-language concepts that may not appear in the command name.

Examples:

```text
memory
video
GPU
safe
downloads
sound
shortcuts
```

Or enter prefiltered:

```text
lk settings memory
lk settings video
lk settings gpu
```

## Layout

The selectable row shows:

```text
CATEGORY   Setting name   current value
```

The preview pane explains what the highlighted item does before changing it.

The header provides a compact status strip:

```text
model … · access … · memory … · shortcuts …
```

The searchable registry covers:

- AI model, host, access, thinking, think display, personality, web key
- AI performance/GPU telemetry and model benchmark
- Living Memory and manual compaction
- file grants and shell shortcut policy
- preferred desktop apps
- Tailscale/Ollama sharing
- sound and motion feedback
- portable profile
- Doctor and versions

## Submenus

File access now provides a small menu for:

```text
Personal folders
Add grant
Remove grant
Inspect grants
Clear grants
```

Preferred apps provide a category picker for:

```text
browser
editor
image
pdf
video
audio
```

Shortcut policy can be switched between `polite` and `force` from settings.

## One source of truth

The control room does not maintain a parallel settings database. It calls the same functions used by direct commands.

For example, changing Thinking in `lk settings` and running:

```text
lk thinking adaptive
```

modify the same configuration.

This keeps commands useful for scripting and muscle memory while making command memorization unnecessary for ordinary configuration.


---

<!-- source: RELEASE-2.5.0.md -->

# Future Crash + LOOK 2.5.0 — Capability platform

Versions:

- Future Crash + LOOK: 2.5.0
- LOOK: 4.5.0
- Future Crash: 1.1.10

## Vision

If the selected Ollama model advertises `vision`, LO can send image bytes with the normal chat request.

```text
lk vision screenshot.png "what is wrong here?"
lo what is in ./photo.jpg
```

Explicit local image paths are attached automatically in LO. A non-vision model reports that vision is unavailable rather than pretending to inspect the image.

## Optional local image generation

ComfyUI is treated as an optional service edge:

```text
lk comfy
lk comfy discover
lk comfy host http://HOST:8188
lk comfy workflow ~/workflows/look-image-api.json
lk comfy output ~/Pictures/LOOK
lk comfy preview on
lk generate "a winter street in Astoria, watercolor"
```

LOOK deliberately does not bundle or auto-download a giant checkpoint. `discover` searches standard Comfy locations and reports existing model files so older installations can be reused.

The configured workflow must be API-format JSON. LOOK substitutes:

```text
__PROMPT__
__NEGATIVE__
__SEED__
```

Generated image files are copied from Comfy's output API into LOOK's configured output folder and can be auto-previewed through the desktop bridge.

## Persistent scheduler

The resident `look_ai.py` service now owns delayed and recurring work:

```text
lk schedule
lk schedule in 30m summarize the project status
lk schedule every 2h check the local service health
lk schedule daily 08:00 give me a morning system report
lk schedule pause ID
lk schedule resume ID
lk schedule remove ID
lk schedule run ID
```

Schedules persist under LOOK state. When due, they become ordinary LO background jobs, so they reuse the existing job queue, access profile, workspace, event receipts, and foreground-priority rules.

Future Crash can use this scheduler as shared infrastructure in a later behavioral pass instead of growing a separate timing system.

## Settings / Doctor

`lk settings` now includes:

- Vision input
- Image generation / Comfy
- Scheduler

`lk doctor` reports the same capability state.

## Installation policy

Ollama remains the only core AI dependency. ComfyUI and image checkpoints are optional. The installer surfaces `lk comfy discover` but does not silently install/download large media models.


---

<!-- source: RELEASE-2.5.1.md -->

# Future Crash + LOOK 2.5.1

Versions:

- Future Crash + LOOK: 2.5.1
- LOOK: 4.5.1
- Future Crash: 1.1.10

## UNSAFE means one thing

Before 2.5.1, LO had two independent permission systems:

- UNSAFE disabled shell-command confirmation.
- filesystem tools still enforced workspace/path grants.

That made this contradictory:

```text
access · UNSAFE
...
LO FILE ACCESS
wants WRITE ~/Downloads/file.txt
```

In 2.5.1 the filesystem transaction receives the active LO access profile.

### Behavior

```text
WORKSPACE
→ current workspace + explicit grants

POWER
→ current workspace + explicit grants
→ shell commands available under POWER confirmation rules

UNSAFE
→ unrestricted filesystem paths under the current user account
→ unrestricted shell command execution for the session
```

UNSAFE still requires the session-level confirmation when entered. It does not prompt again for each filesystem path.

The profile is scoped to each filesystem transaction and restored afterward.


---

<!-- source: RELEASE-2.5.2.md -->

# Future Crash + LOOK 2.5.2

Versions:

- Future Crash + LOOK: 2.5.2
- LOOK: 4.5.2
- Future Crash: 1.1.10

## Persistent UNSAFE consent

The permission model now distinguishes a saved preference from an ad-hoc escalation.

```text
lk ollama access unsafe
→ strong confirmation once
→ saves UNSAFE as the user's chosen profile

lo ...
→ starts UNSAFE directly
→ no repeated session confirmation

lo --unsafe
→ explicit temporary escalation
→ asks for confirmation for that session
```

UNSAFE continues to authorize filesystem paths outside the starting workspace as well as shell commands. WORKSPACE and POWER retain their bounded/grant behavior.


---

<!-- source: RELEASE-2.6.0.md -->

# Future Crash + LOOK 2.6.0 — GPU workstation bootstrap

Versions:

- Future Crash + LOOK: 2.6.0
- LOOK: 4.6.0
- Future Crash: 1.1.10

## Where Comfy lives

ComfyUI belongs on the machine doing GPU inference. On a LOOK setup with a Linux RTX tower and lighter clients, install Comfy on the GPU tower.

The client does not need a local Comfy install merely to use a remote Comfy service.

## Installer behavior

On Linux with an NVIDIA GPU, `install.sh` now offers:

```text
LOOK GENERATIVE MEDIA
  ✓ NVIDIA GPU · ...
  ComfyUI enables local image generation; old model folders can be reused without copying.
  Set up local ComfyUI image generation on this GPU? [Y/n]
```

If accepted, LOOK:

1. scans for previous ComfyUI / A1111 / Forge installs and model folders;
2. reports large checkpoint files found on HOME and common mounted-drive paths;
3. installs or updates a fresh managed ComfyUI codebase;
4. creates an isolated Python virtual environment;
5. installs current NVIDIA PyTorch + Comfy requirements;
6. enables the built-in ComfyUI Manager dependencies;
7. optionally wires old model libraries into `extra_model_paths.yaml`;
8. offers an explicit starter-model menu;
9. writes a managed launcher and LOOK Comfy configuration.

Managed code lives under:

```text
~/.local/share/look/services/comfyui/
```

Large model libraries can remain on other disks.

## Discovery

```text
lk comfy discover
```

scans:

```text
$HOME
/mnt
/media/$USER
/run/media/$USER
```

at bounded depth.

It recognizes:

- ComfyUI roots (`main.py`)
- A1111 / Forge roots
- checkpoints
- diffusion_models / unet folders
- common `.safetensors`, `.ckpt`, `.pt`, `.pth`, and `.gguf` model files

Discovery is read-only.

## Reusing old models

When structural old installs are found, LOOK can generate:

```text
ComfyUI/extra_model_paths.yaml
```

so the new managed Comfy can see the old weights without copying them.

This follows ComfyUI's native external-model-path mechanism.

## Starter models

The bootstrap offers:

```text
[1] Reuse existing models only
[2] SDXL 1.0 base · ready-to-run LOOK starter · ~6.9 GB
[3] FLUX.1 Schnell FP8 · modern fast checkpoint · ~17.2 GB
[4] Both
[5] Skip
```

Downloads are explicit, resumable, and verified with known SHA-256 hashes.

### SDXL starter

SDXL is used as the guaranteed ready-to-run compatibility starter because LOOK ships a simple API-format workflow for it.

Installing SDXL configures:

```text
~/.local/share/look/workflows/sdxl-api.json
```

so after Comfy starts:

```text
lk generate "an old harbor town in winter, watercolor"
```

has a complete model + workflow path.

### FLUX.1 Schnell FP8

The optional Comfy-Org single-file FP8 checkpoint is suitable for a 24 GB-class GPU and is offered as the more modern fast model option. LOOK does not force the SDXL workflow onto FLUX; select/export an appropriate FLUX API workflow before making it the automation workflow.

## Managed service

```text
lk comfy
lk comfy start
lk comfy stop
lk comfy restart
lk comfy discover
lk comfy bootstrap
```

The launcher is:

```text
~/.local/bin/look-comfy
```

and binds Comfy to `127.0.0.1:8188` by default.

`lk generate` attempts to start this managed local service automatically if the configured localhost Comfy endpoint is offline.

## Manager

Current manual ComfyUI installations include the new Manager in core; LOOK installs its manager requirements and starts Comfy with `--enable-manager`.

## Safety / ownership

LOOK never silently downloads a 7–24 GB model. Model downloads are a separate, visible user choice.

Uninstalling LOOK should be treated separately from deleting image models; model libraries may predate LOOK or live on shared/mounted storage.


---

<!-- source: RELEASE-2.6.1.md -->

# Future Crash + LOOK 2.6.1

A surgical Living Memory lifecycle update.

The intended hierarchy is now explicit:

```text
RECENT
  high fidelity, short lifetime, includes sidebars
      ↓
CANDIDATES
  cheap semantic hypotheses, permissive admission, reinforcement + decay
      ↓
DURABLE ATOMS
  earned stable facts/preferences
      ↓
DOMAIN SUMMARIES
  aggressively compressed meaning
      ↓
CORE SUMMARY
  tiny routing/user model
```

`sidebar`, `no need to remember this`, `just for now`, and similar language do **not** mean "ignore this turn." The exchange remains in RECENT normally. They mean "do not promote this into deep memory."

Candidate admission is deliberately somewhat noisy. Durable promotion remains conservative.

`lk memory` now exposes the metabolism:

```text
extraction · ... candidate · ... none · ... local
metabolism · merged N · promoted N · expired N · evicted N
compiler · consolidated N · last ...
```

Schema-2 legacy summary content is migrated into the current durable system when useful and the inactive legacy tier is retired.


---

<!-- source: RELEASE-2.6.2.md -->

# Future Crash + LOOK 2.6.2

A surgical Comfy polish release.

- Empty workflow settings no longer become `Path('.')`.
- `lk generate` now reports `No Comfy workflow configured` instead of an `Errno 21` directory error.
- `lk comfy discover` scans up to three levels beneath recognized checkpoint/diffusion-model roots, catching old model collections organized into family subdirectories.
- The existing working 3090 generation path is unchanged.


---

<!-- source: RELEASE-2.6.3.md -->

# Future Crash + LOOK 2.6.3

A surgical Comfy readiness fix.

`lk comfy` no longer merely echoes a workflow string. It validates the file with the same resolver used by `lk generate`.

When LOOK's packaged starter exists, an empty or stale workflow pointer repairs automatically:

```text
workflow     SDXL starter · ready
             ~/.local/share/look/workflows/sdxl-api.json
```

Manual recovery is now:

```text
lk comfy repair
```

No knowledge of API-format workflow JSON paths is required for the managed SDXL starter.

Managed Comfy is also included in local model inventory, including nested checkpoint/model-family subdirectories.


---

<!-- source: RELEASE-2.7.0.md -->

# Future Crash + LOOK 2.7.0 — Services

Versions:

- Future Crash + LOOK: 2.7.0
- LOOK: 4.7.0
- Future Crash: 1.1.10

## Mental model

A LOOK machine can host several independent localhost services:

```text
Ollama        127.0.0.1:11434
ComfyUI       127.0.0.1:8188
Mercury       configured/discovered port
Web terminal  configured port
```

LOOK exposes them to the private tailnet with separate Tailscale Serve HTTPS listeners.

## Commands

```text
lk services
lk services discover
lk services set mercury PORT
lk services share all
lk services share comfy
lk services unshare all

lk share
lk share status
lk share off
```

Bare `lk share` means: share every configured service that is actually running on this computer.

## Stable endpoints

LOOK deliberately avoids making all services compete for the default Serve endpoint:

```text
Ollama    HTTPS :11435 → LOOK localhost proxy → Ollama :11434
ComfyUI   HTTPS :8188  → ComfyUI :8188
Mercury   HTTPS :PORT  → Mercury :PORT
```

This fixes the class of failure where exposing Comfy could replace the existing Ollama Serve route.

## Mercury Writer

LOOK attempts conservative Mercury discovery from running process command lines/listening ports. It never guesses a port.

If automatic discovery cannot resolve it:

```text
lk services set mercury 8765
lk services share mercury
```

Use Mercury's actual server port.

## Privacy

This uses Tailscale Serve, which is limited to devices/users permitted by the tailnet. LOOK does not automatically use Tailscale Funnel/public internet exposure.


---

<!-- source: RELEASE-2.7.1.md -->

# Future Crash + LOOK 2.7.1

A surgical shell-UX update.

## Force really means force

Default behavior remains polite:

```text
fc → Zsh history builtin
fcr → Future Crash
```

After:

```text
lk shortcuts force
rb
```

LOOK explicitly disables Zsh's `fc` builtin and installs:

```text
fc → Future Crash
```

Real executables remain protected.

## Stateful home

`lk home` no longer assumes optional shortcuts exist.

If aggressive aliases are active it can show:

```text
l look around   lo ask   lk inspect   lh home   fc Future Crash
```

If they are not active, it falls back to canonical truth:

```text
lk look around   lk o ask   lk inspect   lk home home   fcr Future Crash
```

The shell exports its live shortcut ownership state so LOOK can render the actual current environment.

`lh` itself is optional/collision-aware; `lk home` is canonical and always available.


---

<!-- source: RELEASE-2.7.3.md -->

# Future Crash + LOOK 2.7.3

Documentation-only cleanup.

Historical release notes are consolidated into:

```text
docs/RELEASE-HISTORY.md
```

The current release note remains standalone. Repository Markdown file count drops from 106 to 24 without discarding historical release content.


---

<!-- source: RELEASE-2.7.4.md -->

# Future Crash + LOOK 2.7.4

A surgical distributed-Comfy fix.

On a client machine:

```text
configured Comfy?
  ↓ offline
discover Tailscale peers :8188
  ↓ reachable
save remote host → ready
```

Only a Linux machine with an NVIDIA GPU is offered the managed local Comfy bootstrap.

`lk generate` and LO's image-generation tool use the same self-healing discovery before failing, so a newly installed laptop can find a shared 3090 Comfy service without installing ComfyUI or diffusion models locally.

On the GPU host:

```text
lk share
```

On a client:

```text
lk comfy discover
lk comfy
```
