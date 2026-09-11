# LOOK Shell changelog

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

