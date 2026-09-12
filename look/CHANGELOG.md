## 4.0.0 — Explicit state architecture

- Defined program, profile, machine, and runtime state as separate contracts.
- Added schema-versioned profile inventory, backup, export, and restore.
- Restore validates archive paths and creates a local safety snapshot before replacing live profile files.
- Added learned-skills-only export for promoting local AI craft back into distributions.
- Added centralized `feedback` engine with finite motion and optional synthesized sound.
- Added `lk sound` and feedback controls to Settings/Config.
- Non-TTY output remains deterministic and animation-free.

## 3.13.3 — Responsive global find

- `f`/`fznv` no longer precompute a 20k-entry catalog before accepting input.
- Search is streaming again, so fzf accepts keystrokes immediately while paths continue arriving.
- Finder colors/pointer/spinner are aligned with LOOK, while LOOK still owns post-selection actions.

## 3.13.2 — File-action status codes

- `_copy`, `_move`, `_remove`, `_mkdir`, and `_touch` now return status matching their textual result.
- Missing-directory prompts/refusals are failures until the requested mutation actually completes.

## 3.13.1 — Batch transaction hardening

- Replaced undo-length inference with explicit batch transaction IDs.
- Full undo rings and batches larger than the undo limit are now safe.
- Batch rollback is transaction-local and reports the failed source.
- LOOK's interactive Zsh prompt keymap binds bare Escape to cancel while preserving Tab completion.

## 3.13.0 — Local message-passing foundation

- Added Tab-completing destination prompts and simplified path completion for shell file actions.
- Replaced stock-fzf `f`/`fznv` front ends with LOOK-native global find presentation.
- Added temporal memory metadata and age-aware prompt context.
- Explicitly separated historical memory from pending intent.
- Added durable background LO jobs and terminal event delivery.
- Shell prompt hook drains completed LO events without blocking current work.

## 3.12.2 — Active-row contrast

- Active filer row now uses a much stronger cyan/dark contrast in truecolor terminals.
- Classic fallback adds bold to reverse video.

## 3.12.1 — Preserve j/k in filter text

- Filter input no longer consumes lowercase `j` or `k` as movement.
- `J/K` and arrow keys navigate matches while filter text is active.
- Browse/select mode keeps normal `j/k` navigation.

## 3.12.0 — Cross-directory working set

- Marked paths are owned by the filer session rather than a single directory view.
- Navigation never clears the working set.
- Status distinguishes local selection from cross-directory selection with color and `N / H HERE`.
- `X` clears the set.
- `<` is now filesystem parent; the temporary `>` binding is retired.

## 3.11.0 — Parent directory key

- In the plain filer browse state, `>` moves to the real filesystem parent.
- Parent navigation and history navigation are now separate concepts.
- Filter-entry mode still accepts `>` as normal text.

## 3.10.5 — Simpler filer keys

- `j/J` moves down; `k/K` moves up; arrows work as expected.
- `L` is reserved for handing the selected/marked working set to LO.
- Removed the unnecessary semicolon and pseudo-horizontal/home-row navigation bindings.

## 3.10.4 — Selected paths become LO context

- In filer FILTER/SELECT mode, `L` launches LO with the marked paths as its working context.
- One unmarked highlighted path works the same way.
- Paths are passed as a manifest, not bulk file contents.
- LO's bounded workspace is rooted at the nearest common selected directory and its banner reports the context count.

## 3.10.3 — Execution contract

- Explicit local filesystem mutation requests must now produce an actual mutation tool call before LO may report success.
- Prose-only mutation plans receive one silent tool-required repair pass.
- Added bounded read-only host process, listening-port, and system snapshot tools for routine diagnostics in Workspace.
- Added one extra tool-loop round for multi-step host work.

## 3.10.2 — lmv/lcp argument hardening

- Multi-source `lmv` and `lcp` now copy argv to an array, pop the final destination, and pass only true sources to the batch engine.
- This removes an ambiguous Zsh parameter-slice expression that could accidentally include the destination as a source.

## 3.10.1 — Continuity and reliable batches

- Added literal cross-session recent conversation, distinct from semantic candidate and long-term memory.
- Fixed long-term consolidation so useful candidates can graduate while strong rather than merely decay forever.
- Added batch text-file creation for multi-file LO requests with unified undo.
- Added multi-source `lcp`, `lmv`, and `lrm` command-line forms.
- Added paging to the terse command index.

## 3.10.0 — Human-sized map

- Added five keyboard control surfaces: system, AI, network, maintenance, and configuration.
- Added compact starter help and a terse complete command index.
- Preserved direct expert commands and added short aliases for models, benchmark, and web status.
- The maintenance surface is intentionally conservative and performs no broad automatic cleanup.

## 3.9.1 — Hidden games

- Added undocumented `lk ttt` and `lk gtnw` terminal Easter eggs.
- Added dual spatial keyboard controls for tic-tac-toe and a perfect minimax opponent.
- Added a randomized abstract WOPR-style simulation with restart, speed control, and clean terminal restoration.
- `lk games` reports `No games installed.`
- Added a rare home-screen `SHALL WE PLAY A GAME?` Easter egg.

## 3.9.0 — Canonical information edges

- LO gained direct weather, place, and Wikipedia tools.
- Live weather uses Open-Meteo current + forecast data instead of search snippets.
- Geographic name resolution uses Open-Meteo geocoding.
- Wikipedia search provides compact canonical article matches for stable background knowledge.
- Generic web search remains available for everything that does not fit a canonical edge.
- Each retrieval announces itself in the terminal so information flow stays visible.

# LOOK Shell changelog

## 3.8.1 — Explicit model-resource policy

- LO now uses an explicit 8192-token context window with bounded recent working history.
- `light`, `adaptive`, and `deep` now drive Ollama thinking behavior on thinking-capable models instead of acting only as prompt guidance.
- Interactive output ceilings are 800 / 1400 / 2000 tokens respectively.
- Memory and learned-skill housekeeping use small no-thinking budgets.
- History trimming preserves complete user-led tool transactions rather than retaining arbitrary transcript tails.

## 3.8.0 — personality + live thinking

- Personality packs: LO, Space Robot, Max, Philosopher.
- Thinking depth: light/adaptive/deep.
- Thinking display: compact/full/quiet with streaming response handling.
- Settings/completion/docs synchronized.


## 3.7.2 — lmk directory-entry fix

- `lmk -d` and prompted directory creation now call `_mkdir` directly and then `cd` only when the directory exists.


## 3.7.1 — prompt input fix

- `_look_prompt` now suppresses terminal echo before LOOK renders typed characters.
- Adds `_look_choice` for immediate `lmk` d/f/y/n decisions.


## 3.7.0 — smart make

- `lmk` creates files or directories from one command.
- Adds journaled empty-file creation and safe undo.
- `mkd` now delegates to journaled `lmk -d`.
- Adds `_lmk` completion.


## 3.6.4 — media status feedback

- `lk media` uses direct state/artist/title queries.
- `mm`, `mn`, `mp`, and full media actions report resulting track/state.


## 3.6.2 — macOS media detection fix

- `lk media` now detects Music and Spotify directly through AppleScript.


## 3.6.1 — fast media aliases + paged intelligence views

- Adds `mm`, `mn`, and `mp`.
- Adds pager behavior to `lk memory` and `lk skills`.


## 3.6.0 — media transport + portable intelligence versions

- Adds `lk media` with macOS Music/Spotify and Linux MPRIS adapters.
- Adds memory schema version 1.
- Adds skills schema version 1 and bundled skills pack version 1.
- Adds `lk skills version` and `lk skills update [FILE]`.
- Preserves locally Learned skills while refreshing Bundled craft.


## 3.5.1 — durable memory lifecycle

- Explicit durable-memory intent promotes into the long-term summary immediately.
- Adds duplicate candidate consolidation.
- Adds periodic long-term summary pruning under a fixed budget.


## 3.5.0 — unified version safety + Zsh command grammar

- Establishes LOOK 3.5.0 as the component baseline inside Future Crash + LOOK 1.2.0.
- Adds context-sensitive Zsh completion for `lk` and `lo`.
- Completes Ollama, memory, skills, system commands, and saved remote host names.
- Unified installer records component versions and refuses accidental downgrade from version-aware releases.
- LOOK runtime behavior from 3.4.4 is otherwise preserved.


## 3.3.3 — thinking-output compatibility

- Prefer Ollama's structured `message.thinking` field when available.
- Continue supporting normal `<think>...</think>` model-template output.
- Add Qwen compatibility for responses where the opening `<think>` is stripped but the closing `</think>` remains.
- Render reasoning under muted/italic `thinking ›` and the final response under normal `lo ›`.
- No streaming, capability, tool, filesystem, remote-host, settings, or installer behavior changed.


## 3.3.2 — installer man-page path fix

- Fixes the 3.3.1 installer error `SCRIPT_DIR: unbound variable`.
- The optional user man-page install now uses the installer's existing `ROOT` source directory.
- No runtime, settings, LO, filesystem, or documentation behavior changed.


## 3.3.1 — documentation synchronization

- Synchronizes README, `lk help`, migration notes, installer metadata, repository command reference, and Unix man page with LOOK 3.3.
- Restores `lk.1` to the release and documents `lk settings`, all LO access profiles, and the full Ollama host/share/key/access grammar.
- Adds `docs/COMMANDS.md` as a compact repository reference; this is documentation only, not a `tldr` integration.


## 3.3.0 — unified settings + LO presentation

- Adds `lk settings`, a single interactive panel over existing access-profile, Ollama-host, preferred-model, web-key, and Tailscale-share controls.
- The settings panel creates no second configuration system; direct commands and existing state remain canonical.
- Thinking-capable model output now renders `<think>...</think>` as a muted/italic `thinking ›` section, visually separate from the final `lo ›` response.
- Existing `file ›`, `command ›`, and `search ›` activity remains distinct.
- No capability semantics, confirmation rules, filesystem behavior, remote routing, or installer ownership model changed.


## 3.2.0 — LO capability profiles

- Adds `conservative`, `workspace`, `power`, and `unsafe` LO access profiles; existing workspace behavior remains the default.
- Adds `run_command` only in power/unsafe sessions. Commands execute on the computer running LOOK even when inference comes from a remote Ollama host.
- Power confirms every shell command; unsafe asks once on session entry and then skips per-command prompts.
- `lk ollama access [MODE]` inspects/sets the persistent profile; `lo --MODE` overrides it for one session.
- Access flags compose with `@HOST` in either order.
- `lk ollama` now reports the selected access profile.
- No existing filesystem, clipboard, filter, undo, remote-host, or installer grammar was removed.


## 3.1.8 — consistent directory resolution

- `ll`, `ld`, `lf`, `lt`, `lr`, and `lz` now resolve directory arguments the same way as `l`: exact directory first, otherwise zoxide shorthand.
- Specialized views keep their existing mode and do not change the parent shell directory.
- No filter, selection, clipboard, Ollama, installer, undo, or file-operation behavior changed.


## 3.1.7 — public shell hygiene

- Removed four personal/project-specific aliases that had accidentally shipped in the public shell fragment.
- Audited shipped shell/config/code files for personal usernames, absolute home paths, and private project launchers.
- No LOOK-owned aliases, functions, interaction grammar, Ollama behavior, installer behavior, or file operations changed.


## 3.1.6 — polite shell integration

- Installer no longer replaces `~/.zshrc` wholesale.
- Existing `.zshrc` is still timestamp-backed up before any edit.
- LOOK shell configuration now lives in `~/.config/look/look.zsh`.
- Installer adds/normalizes one marked source block in the user's existing `.zshrc`.
- Reinstall/update refreshes only LOOK's owned fragment.
- `lk uninstall` removes the marked hook and fragment; legacy installs retain backup restoration behavior.
- No LOOK interaction, Ollama, clipboard, filter, navigation, or file-operation behavior changed.


## 3.1.5 — filter footer label

- Restore `E edit` to the interactive filter/select footer. Edit behavior was already intact; only its visible command hint had been lost.
- No runtime behavior changed.


## 3.1.4 — documentation reconciliation

- Audited the executable command dispatch, Zsh shortcuts, Ollama host/share/key grammar, and interactive file controls against the documentation.
- `lk help` is now the complete in-terminal command/key glossary, including Ollama `share status/off`, `key/status`, host selection/forget, uninstall, undo, webterm, and the full selection action language.
- README Reference now carries the same canonical command map, organized by intent.
- No runtime behavior changed.


## 3.1.3

- Make Ollama model choice host-aware: keep the preferred model when installed on the selected host, otherwise use a resident or installed model instead of surfacing Ollama's model-not-found 404.
- Restore `O open with` to the wrapped interactive filter/select footer; the action itself was never removed.


## 3.1.2 — Tailscale permission handoff

- `lk ollama share` keeps the localhost Host-rewrite proxy alive when Tailscale Serve requires root/operator permission.
- On that permission failure, LOOK prints the exact one-time `sudo tailscale serve --bg 11435` handoff instead of tearing the proxy back down.
- `lk ollama share off` gives the matching sudo handoff when needed.
- LOOK never invokes `sudo` itself and does not alter Tailscale operator configuration.


## 3.1.1 — Ollama share fix

- `lk ollama share` now places a tiny localhost-only proxy between Tailscale Serve and Ollama.
- The proxy rewrites the public tailnet `Host` header to `localhost:11434`, preserving Ollama's host protection while allowing private Tailscale Serve access.
- No new dependency, installer layer, command grammar, or unrelated behavior changes.


## 3.1.0 — Ollama anywhere

- Adds named Ollama host profiles while keeping `local` as the permanent built-in default.
- `lk ollama host` lists saved hosts and discovers reachable Ollama servers on Tailscale peers using their device hostnames.
- `lk ollama host NAME` selects a persistent default; `lk ollama host NAME URL` saves/selects an explicit endpoint.
- `lo @NAME` uses a host for one session without changing the default.
- `lk ollama share` shares localhost Ollama inside the tailnet through Tailscale Serve; `share status` and `share off` are included.
- Ollama inspection, model control, benchmarks, web search, memory, and workspace tools follow the selected host.
- Tailscale remains optional; local LOOK behavior is unchanged when it is absent.


## 3.0.5 — escape polish

- Hidden Ollama key entry: Esc, Ctrl-C, Ctrl-D, or empty Enter cancels cleanly.
- LO: Ctrl-C during thinking/searching cancels the current turn and returns control instead of tearing down the session.
- Filter typing captures queued keystrokes before redraw with a 12 ms idle gap instead of 55 ms.
- No command grammar, selection semantics, clipboard behavior, undo, or installer scope changed.


## 3.0.4 — Ollama key setup

- Adds `lk ollama key` and `lk ollama key status`.
- Excludes `key` from the historical long-form Ollama chat route, so these commands are handled locally rather than sent to `lo`.
- README encourages optional free Ollama account/API-key setup for web search.
- No other LOOK behavior changed.


## 3.0.3 — GitHub install instructions

- Removes the brittle guessed `/releases/latest/download/look-shell.zip` recipe.
- Documents two dependable install paths: GitHub Releases and Code → Download ZIP.
- Explains why `chmod +x install.sh` is needed after GitHub ZIP downloads.
- Makes clear that the installer is folder-name agnostic; `look-shell-main` and versioned release folders both work.
- No LOOK interaction, clipboard, selection, undo, uninstall, installer dependency, or LO behavior changed.


## 3.0.2 — clean exit

- Adds `lk uninstall`.
- Installer records exact package/add-on ownership for safe removal later.
- Uninstall restores the recorded pre-LOOK `.zshrc`, while preserving the current LOOK-era `.zshrc` as a timestamped recovery copy.
- `~/.zsh_secrets` is never removed.
- Homebrew/Linuxbrew itself is never automatically removed.
- README adds a copy/paste GitHub `releases/latest/download/look-shell.zip` installation path.
- No browser, clipboard, mark, navigation, undo, or LO grammar changed.


## 3.0.1 — complete mark toggle

- `A` now toggles the entire current match set: mark all when any are unmarked; clear all when all are already marked.
- This works with live filters, so `A` can select or deselect exactly the visible match set.
- No other selection, clipboard, navigation, undo, installer, or LO behavior changed.


## 3.0.0-beta.16 — onboarding and installer

No filesystem/browser grammar changed.

- The installer now explicitly treats LOOK as an opinionated workstation: `fd`, Chafa, Poppler, `ttyd`, and `lsof` join the existing core toolset.
- Tailscale is offered as the Remote layer (default Yes); Ollama is offered as the AI layer (default No).
- `--yes` accepts optional layers; `--no-optional` installs only the workstation.
- `webterm()` now explains missing requirements instead of falling through to shell errors.
- The first LOOK-initiated Neovim edit teaches `Esc`, `:q`, `Enter` once.
- README is rewritten around LOOK's present-day mental model rather than release archaeology.
- Documentation stays deliberately small: `README.md`, `CHANGELOG.md`, and the built-in `lk help`.

