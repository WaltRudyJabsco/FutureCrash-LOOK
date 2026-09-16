## 3.1.0 — Structured tool truth

- Adds internal `ToolResult`: ok, status, message, data.
- The transaction layer no longer guesses success from arbitrary English.
- Legacy filesystem runners are normalized through one explicit family adapter.
- Move/copy/remove/write/mkdir/open/preview success contracts are explicit.
- Failed/refused mutations are journaled as failures even when their human message changes.
- Repeat/replay preserve the underlying tool's truth contract.
- LOOK 4.31.0.

## 3.0.1 — Transaction truth hotfix

- `lk tooling-audit` uses canonical `_load_lo_profile()`.
- Successful filesystem mutations render from their authoritative receipt.
- Open/play verification can no longer overwrite successful mutation truth.
- LOOK 4.30.1.

## 3.0.0 — LO tool harness

- Fixes receipt JSONL root cause and repairs recoverable 4.20–4.22 journals.
- Central tool transaction: execute → classify → journal → return.
- Filesystem, URL, inspection, capability, command, repeat and replay edges share the harness.
- Declarative model-independent tool/profile policy.
- `lk tooling-audit` exposes the contract.
- Bounded journal remains 2 MB current + five archives.
- LOOK 4.30.0.

## 2.12.0 — Typed resources + graded receipts

- Web candidates now carry deterministic resource types, including YouTube video/channel/playlist/search.
- Play/watch intent requires a playable YouTube video candidate; channels and profile pages are rejected rather than launched.
- `open_url` accepts explicit open/play/watch intent and enforces YouTube media typing.
- Local media launch receipts are now `DISPATCH OK`: launcher handoff is not promoted into playback truth.
- LO rendering says the launcher was handed the resource, not that VLC is definitely playing it.
- LOOK 4.22.0.

## 2.11.0 — Resource routing and action harness

- Unifies LO's resource geography: unqualified requests stay local; explicit online/site intent routes outward.
- Adds verified `open_url` browser action for exact http/https resources.
- Web discovery can now cross the missing search-result → browser-action edge.
- URL launch is receipt-gated exactly like local host actions.
- Session referents/repeat actions support both local paths and web URLs.
- Receipt viewer counts only valid action records.
- Architecture audit now reports resource routing and both action edges.
- LOOK 4.21.0.

## 2.10.3 — Observable truth + receipts

- `OPEN OK` now means exactly “dispatched successfully,” not “still running” or “currently playing.”
- Final rendering downgrades unsupported playback/process claims to receipt-supported language.
- Adds `lk receipts [N]` to inspect the bounded forensic action journal.
- Architecture audit documents dispatch-vs-runtime truth boundary.
- LOOK 4.20.3.

## 2.10.2 — Verified-action final gate

- Fix conversational continuations (`yes`, `try again`, `go ahead`) bypassing external-action intent detection.
- Known verified referents replay deterministically for confirmations/retries.
- Adds an unconditional final-render invariant: success prose cannot leave LO without a positive host receipt in the current turn.
- If prose claims success and a verified referent exists, LOOK performs the exact known action itself before rendering.
- LOOK 4.20.2.

## 2.10.1 — Verified actions

- Host-visible success claims are now receipt-gated.
- Open/play/preview/reveal requests get one deterministic repair turn if the model answers in prose without executing the tool.
- LO cannot claim “playing/opened/launched” without a successful host tool receipt.
- Successful external actions feed the existing session referent/repeat register.
- Fix Python 3.14 `re.split` maxsplit deprecation warning.
- LOOK 4.20.1.

## 2.10.0 — Conversational task continuity

- Adds an ephemeral session referent/action register.
- `again`, `play it again`, `that again`, and similar repeats replay the exact successful action without another model turn or filesystem search.
- Successful open/play/preview/reveal actions become the current referent for ordinary `it`/`that` follow-ups.
- Fuzzy discovery guidance favors one semantically broadened locator request over repeated search spray.
- LOOK 4.20.0.

## 2.9.9 — Post-success formatter hotfix

- Remove leaked locator confidence code from `_ollama_markup`.
- Preserve locator confidence reporting inside `search_files`.
- Architecture audit now exercises the terminal formatter.
- LOOK 4.19.2.

## 2.9.8 — Runtime hotfix

- Fix AI-pool loader calling nonexistent `_read_json`.
- Fix locator token regex that reduced normal queries to zero tokens.
- LOOK 4.19.1.

## 2.9.7 — Execution architecture audit

- Audited actual LO call graph instead of intended behavior.
- `search_files` now defaults to cwd-independent `personal` scope.
- Filesystem dispatcher receives access profile explicitly; discovery routing no longer depends on a mutable profile global.
- Fixed malformed raw-shell-search guard that allowed `find`/`mdfind` proposals through.
- Inspection-repair path can no longer reintroduce filesystem shell searches.
- Adds `lk architecture-audit`.
- LOOK 4.19.0.

## 2.9.6 — Busy-cycle escape + locator enforcement

- Power/unsafe broad discovery can no longer fall into the legacy home-folder grant prompt.
- Shell `find`, `mdfind`, `fd`, `locate`, and `plocate` are denied as agent fallbacks; `search_files` is the sole discovery edge.
- Agent shell commands default to 20 seconds and are capped at 60 seconds.
- Busy indicators explicitly advertise `Ctrl-C cancel`.
- Adds `lk locator-test`, a model-free acceptance test for POWER access and locator latency.
- LOOK 4.18.0.

## 2.9.5 — Observable tasks + AI pool foundation

- Locator now streams stage telemetry: context, likely folders, OS index, fallback, candidate count, elapsed time.
- Adds durable `lk ai-pool` configuration for primary, fast, background, and fallback model roles across hosts.
- Existing model selection remains the primary execution path; pool roles are additive and safe to configure before routing is enabled.
- Chat header shows configured fast-role routing.
- LOOK 4.17.0.

## 2.9.4 — Adaptive locator

- Search rings: context → likely folders → OS index → shallow fallback.
- macOS uses Spotlight; Linux uses plocate/locate when available.
- Three-second locator budget; no recursive home crawl.
- LOOK 4.16.0.

## 2.9.3 — Interactive agent contract

- `list_files` is now strictly one known directory, non-recursive, bounded to 120 entries.
- Find/search/locate is explicitly routed conceptually to `search_files`; shell/list crawling is forbidden by the agent contract.
- Ordinary user-root reads bypass path-grant prompts in normal profiles.
- Search results report STRONG / PLAUSIBLE / WEAK evidence for semantic evaluation.
- LO is instructed to ask a quick clarification on plausible mismatches rather than spin or blindly act.
- Tool success and task success are explicitly separate.
- Structured returned paths flow directly into open/play.
- LOOK 4.15.0.

## 2.9.2 — Workspace is context, not a sandbox

- Access profiles govern authority rather than using cwd as a sandbox.
- Conservative broadly reads/searches/opens ordinary user files but exposes no mutation tools.
- Workspace broadly uses personal files through journaled LOOK tools without shell access.
- Power has current-user filesystem authority plus shell; risky commands still confirm.
- Unscoped file discovery begins at home in every profile.
- Find/search/open/play/read intent is explicitly non-mutating.
- LOOK 4.14.0.

## 2.9.1 — Specialized tools first

- Ranked progressive filename/path matching tolerates mistaken or extra query words.
- In UNSAFE sessions, an unscoped file search begins at the user's home rather than the current repository.
- Raw shell `mdfind`/`find`/`fd`/`rg` discovery is rejected in favor of LOOK's structured search tools.
- A shell command that exits 0 with no output is explicitly marked `NO TASK PROGRESS`.
- Structured paths continue directly into `open_path`, avoiding shell quoting problems with spaces, brackets, parentheses, and Unicode.
- LOOK 4.13.1.

## 2.9.0 — LO acts, records, and keeps moving

- Fix LO file discovery: `search_files` is path/name-only and never reads arbitrary binary file contents.
- Add explicit bounded `search_content` via ripgrep for textual content searches.
- Add media-aware `open_path` intent; requested playback prefers configured `LOOK_MEDIA_PLAYER`, then VLC when available.
- Add compact append-only LO action receipts under `~/.local/share/look/receipts`, rotated at 2 MB with five archives retained.
- Add repeated-identical-tool-call loop protection and the first bounded task-trace seam for future checkpoint/continuation work.
- LOOK 4.13.0.

## 2.8.9 — Living Memory flow correction

- Extraction now favors recall while metabolism supplies precision.
- Add high-recall candidacy for user-authored project decisions, architecture, workflows, and preferences.
- Sidebar/temporary material is RECENT-only; old transient contamination is pruned automatically.
- Tighten automatic durable promotion to require repeated evidence.
- Add deterministic domain/core compiler fallbacks.
- Add extraction-reason diagnostics and candidate-starvation health warning.
- LOOK 4.12.0.

## 2.8.8 — Doctor hotfix

- Fix `lk doctor` NameError when Ollama is reachable but no model is currently loaded.
- Doctor now reads the canonical shared active model before reporting the on-demand model.
- No model-routing or navigation behavior changed.

## 2.8.7 — One active model

- Establish one shared active Ollama model as the default for LOOK, LO, Future Crash Oracle, Ask, Workstation, and background AI work.
- Rename the internal `preferred` concept to `active`: selecting a model means this is the model the environment should actually call.
- Loaded Ollama models are telemetry only and can no longer silently override the active model.
- LO now refuses with a clear message if the active model is unavailable on the selected host instead of silently choosing an arbitrary loaded/installed model.
- Future Crash rereads the shared active model before every frame and every inference unless launched with explicit `--model`.
- Future Crash Ambient, Ask, and Workstation headers now label the model as `shared` or `override`.
- Background memory/skill workers fall back to the shared active model rather than a hard-coded qwen3:8b default.
- Model selection still unloads other loaded models and preloads the chosen model, preserving the single-model 3090 performance path.
- LOOK 4.11.0; Future Crash 1.1.14.

## 2.8.6 — Progressive global search hotfix

- Fix `ff` / `fznv` blocking on a full home-directory scan before accepting input.
- Global LOOK FIND now opens immediately and discovers files progressively in a daemon thread.
- Seed the catalog with the search root's immediate children before recursive discovery.
- Stream `fd` output line-by-line when available; fall back to progressive `os.walk`.
- Every filter/action refresh reads the growing live catalog.
- Show a quiet `scanning…` indicator in the LOOK FIND header while discovery continues.
- Preserve the unified LOOK renderer/actions, including `G` go-to-shell behavior.
- Future Crash remains 1.1.13.

## 2.8.5 — Unified LOOK navigation

- Consolidate navigation around LOOK rather than adding more shell verbs.
- `cd` stays native Zsh and `z` stays native zoxide.
- `l` remains the smart front door: exact live filesystem first, unique live child fuzzy match second, zoxide history/frecency third, global LOOK search as the final fallback.
- Ambiguous live child matches now open LOOK already filtered to the typed query instead of choosing arbitrarily.
- `l <Tab>` merges native live-directory completion with zoxide history candidates; live filesystem truth is no longer replaced by stale history.
- `ff [QUERY]` now opens LOOK's own global FIND renderer instead of a separate fzf UI.
- `fznv [QUERY]` uses the same LOOK FIND UI and opens the chosen file in Neovim.
- Global LOOK FIND supports seeded queries and the same selection/actions vocabulary as normal LOOK.
- `G` from global search now truly exits to the selected directory (or selected file's parent) through the existing shell handoff.
- Remove the now-unused legacy fzf picker implementation from LOOK's shell layer.
- Clean stale command/help references left over from older `f`/`fc` ownership.
- Future Crash remains 1.1.13.

## 2.8.4 — Navigation + model-state coherence

- Restore native Zsh `cd` completely; LOOK no longer wraps or replaces shell directory navigation.
- Keep `l` as the smart/fuzzy navigation front door: explicit existing paths win, otherwise zoxide resolves history/frecency.
- `l <Tab>` now reuses the exact completion function registered for `z`, so LOOK navigation and zoxide completion stay in sync instead of maintaining parallel candidate logic.
- Remove the experimental shell `g` / `go` commands. Uppercase `G` inside LOOK remains the single "go there" bridge back to the shell.
- Model panel terminology is now `TEST / LOAD / SELECT` rather than ambiguous enabled/resident/preferred language.
- Model rows are width-aware and capability labels are compacted to reduce overflow.
- `X` toggles test inclusion and immediately reloads persisted state before redraw.
- Stale test-exclusion entries for models no longer installed are pruned automatically.
- Future Crash now follows LOOK model selection live unless launched with an explicit `--model` override; ambient telemetry and Workstation display use the current Oracle model rather than frozen startup arguments.
- Future Crash bumps to 1.1.13; LOOK to 4.9.4.

## 2.8.3 — Navigation semantics

- Restore smart `cd`: existing filesystem paths and native forms always win; otherwise zoxide history/frecency is used as a fallback.
- Restore explicit Zsh directory completion for the smart `cd` function.
- Add one semantic GO action through collision-aware `g` / `go`: directories become cwd; files move to their parent and reopen LOOK with that file selected.
- Unify LOOK's uppercase `G`: in filter/select mode it goes to the selected item; in ordinary browse mode it exits LOOK into the directory currently being browsed.
- Lowercase `g` remains "top of view"; uppercase `G` is now consistently "go."
- `l -` remains previous-directory + LOOK.
- Future Crash remains 1.1.12.

## 2.8.2 — Command ownership cleanup

- Fix `f` Future Crash shortcut being overwritten later in shell startup by LOOK's legacy fuzzy-finder `f()` function.
- Rename LOOK fuzzy find to `ff`.
- In force shortcut mode, `f` now reliably resolves to Future Crash.
- Restore Zsh's native `fc` builtin explicitly during startup/migration: remove old LOOK aliases/functions named `fc` and re-enable the builtin.
- `fc` is permanently reserved for Zsh history; LOOK no longer attempts to repurpose it.
- Retire only legacy LOOK-owned `f` fuzzy functions when migrating an already-running shell; unrelated user `f` functions remain protected under polite mode.
- Future Crash remains 1.1.12.

## 2.8.1 — rb hotfix

- Fix LOOK deleting its own `rb()` function later in `look.zsh` after defining it successfully near the top.
- Keep early reload-safety cleanup intact so stale aliases are still removed before function parsing.
- `rb` again resolves to LOOK's shell function after install/reload.
- No other runtime behavior changes.
- Future Crash remains 1.1.12.

## 2.8.0 — Shell grammar + deterministic tools

- Add personal `f` → Future Crash through the existing polite/force collision policy. `fc` is permanently native Zsh.
- Add `l -` previous-directory toggle followed by LOOK orientation.
- Formalize `lmk` options: `-d/--dir`, `-f/--file`, `-p/--parents`, and `--`; reject unknown flags instead of treating them as paths.
- Add `lk match GLOB [v|t|n] [--all]`: deliberate wildcard matching ranked by natural version, modification time, or name.
- Version ranking handles multi-part numeric filenames naturally (`2.10.0` > `2.8.0`).
- Add a deterministic translation edge for a configured LibreTranslate-compatible service: `lk translate TO TEXT` or `lk translate FROM TO TEXT`.
- Translation does not silently fall back to model guessing; it identifies/configures its provider explicitly.
- Portable-user-memory / device-state separation and home-node sync remain architecture work, not silently introduced in this release.
- Future Crash remains 1.1.12.

## 2.7.9 — Zsh reload + paste safety

- Fix fresh install/reload parse error: `defining function based on alias 'rb'`.
- Clear LOOK-owned aliases/functions immediately after Oh My Zsh loads, before any LOOK function definitions are parsed.
- Stop shadowing/disabling Zsh's real `fc` builtin, even in force-shortcut mode.
- Root cause: Zsh/ZLE history and bracketed-paste machinery legitimately invokes `fc` with flags such as `-p -a /dev/null` and `-P`; our Future Crash shortcut was intercepting those internal calls.
- Preserve the ergonomic typed `fc` shortcut safely: in force mode, the ZLE `accept-line` widget rewrites an interactive command line containing exactly `fc` to `fcr`.
- Internal `fc ...` history/paste calls continue to resolve to Zsh's native builtin.
- Future Crash remains 1.1.12.

## 2.7.8 — Dead working-directory recovery

- Fix LOOK commands crashing after an undo/move/remove operation invalidates the directory the shell is currently standing in.
- Add a process-wide safe-CWD resolver: LOOK recovers to the nearest surviving ancestor, then home as a final fallback.
- `lk home`, LO, profile export, scheduler/background jobs, disk inspection, and other current-directory consumers now share the safe resolver.
- Add a Zsh `precmd` recovery hook so the parent shell repairs itself before the next prompt.
- `rb` repairs the working directory before `exec zsh`, avoiding zoxide/Perl/File::Find initialization noise from a deleted CWD.
- LOOK and LO entry points defensively repair the shell directory before launching.
- Tested against a genuinely deleted current directory; `lk home` now returns normally.
- Future Crash remains 1.1.12.

## 2.7.7 — Future Crash interactive-submit reliability

- Fix A/Ask and X/Workstation Enter appearing to hang when Future Crash already has Oracle work in flight.
- Interactive input is no longer silently discarded while `busy`; it is queued and visibly dispatched as soon as the current Oracle call releases.
- Offline submits preserve the typed input and show an explicit Oracle-offline notice.
- Background Oracle calls (ambient, fortune, memory, scheduled thread work) now have a bounded 18-second network timeout so they cannot monopolize the UI for two minutes.
- Future Crash now inherits LOOK's selected model as well as LOOK's selected Ollama host.
- This avoids needless shared-GPU model churn/loading when LO and Future Crash point at the same remote 3090.
- Explicit `--model` and `--ollama` overrides still win.
- Future Crash bumps to 1.1.12; LOOK to 4.8.1.

## 2.7.6 — LO typography

- Give LO chat a dedicated typographic presentation while preserving terminal-native interaction.
- Compact the startup banner into an instrument-style header with model, host, connection, access, thinking, workspace, capabilities, and controls.
- Present YOU and LO as clear conversational blocks instead of repeated inline `you ›` / `lo ›` prefixes.
- Make thinking visually subordinate and keep compact thinking's in-place rolling behavior.
- Present filesystem, command, image, schedule, and system activity as terse labeled receipts.
- Quiet background memory/reflection notices.
- Add tiny reusable LO rendering primitives for width, rules, labels, speakers, and receipts.
- No TUI framework dependency; ANSI/Unicode only.
- Future Crash remains visually and behaviorally unchanged at 1.1.11.

## 2.7.5 — Future Crash inherits LOOK Ollama host

- Future Crash now defaults to LOOK's currently selected Ollama host.
- Explicit `--ollama URL` still wins.
- If LOOK has no valid selected host, Future Crash falls back to `http://127.0.0.1:11434`.
- Fixes client machines where LO worked against a shared 3090 while Future Crash telemetry showed `ORACLE LINK OFFLINE`.
- Future Crash bumps to 1.1.11.

## 2.7.4 — Comfy client discovery

- Fix client machines being encouraged to install ComfyUI locally when the intended GPU service lives on another LOOK machine.
- `lk comfy discover` now checks the configured host first, then probes online Tailscale peers on the dedicated Comfy HTTPS port `:8188`.
- A reachable remote Comfy service is saved automatically as the client's default host.
- If several services are available, a peer named like the 3090 workstation is preferred; otherwise LOOK chooses the first stable discovered service and reports it.
- Non-GPU clients no longer fall through to the local Comfy bootstrap/install path.
- Local Comfy bootstrap/discovery remains available on Linux NVIDIA workstations.
- `lk generate` and LO's `generate_image` tool perform the same remote self-heal before reporting Comfy unavailable.
- Failure guidance now tells clients to share Comfy from the GPU host rather than install redundant local models.
- Future Crash remains 1.1.10.

## 2.7.3 — Documentation consolidation

- Consolidated 83 historical `docs/RELEASE-*.md` files into one `docs/RELEASE-HISTORY.md`.
- Kept the current release note as a standalone document.
- Preserved architectural/how-to documentation as separate focused files.
- Reduced repository Markdown file count from 106 to 24.
- No runtime behavior changes.

## 2.7.2 — Future Crash return semantics

- `future-crash`, `rst`, `fcr`, and force-mode `fc` now share one semantic action.
- From a normal shell they launch Future Crash.
- From Future Crash's escaped child shell they cleanly exit that shell and return to the existing Future Crash parent session.
- Removes the old "already inside Future Crash" dead-end behavior and avoids recursive Future Crash processes.
- Makes `fc` an intentional return command, reducing accidental Ctrl-D exits.
- Future Crash remains 1.1.10.

## 2.7.1 — Stateful shell shortcuts

- `lk shortcuts force` now truly reclaims the Zsh `fc` builtin for Future Crash by explicitly disabling that builtin and binding `fc → fcr`.
- Default/polite installs continue to leave native `fc` untouched.
- `lh` is now collision-aware rather than unconditionally installed; canonical `lk home` always works.
- Zsh exports the actual live shortcut state into LOOK so UI can report reality rather than a hypothetical alias map.
- `lk home` dynamically shows `l`/`lh`/`fc` only when they actually resolve to LOOK; otherwise it shows canonical `lk`, `lk home`, `lk o`, and `fcr` forms.
- The shell command glossary is now state-aware and shows active optional aliases plus current shortcut policy.
- Help text distinguishes permanent canonical/fast commands from optional convenience aliases.
- Future Crash remains 1.1.10.

## 2.7.0 — LOOK services + tailnet sharing

- Add a unified local service registry and `lk services`.
- Add `lk share` as the simple "share whatever useful is running here" command.
- `lk services status` shows local service state and Tailscale Serve state together.
- `lk services share all` exposes only configured services that are actually running locally.
- `lk services unshare all` removes LOOK-managed Tailscale Serve endpoints.
- Ollama and ComfyUI now use separate deterministic Tailscale HTTPS ports, preventing one service from replacing the other.
- Ollama tailnet HTTPS endpoint moves to dedicated port 11435; host discovery understands the new endpoint.
- ComfyUI uses HTTPS port 8188.
- Mercury Writer is a first-class optional service: LOOK attempts conservative process/port discovery and otherwise supports `lk services set mercury PORT`.
- Generic web terminal slot is also available for explicit configuration.
- Settings REMOTE surface now controls all tailnet services rather than Ollama alone.
- Tailscale Serve is used only for tailnet-private sharing; LOOK does not enable Funnel.
- Future Crash remains 1.1.10.

## 2.6.3 — Comfy workflow self-healing

- `lk comfy` and `lk generate` now share one validated workflow resolver.
- Empty/stale workflow config self-heals to LOOK's installed `sdxl-api.json` starter when available.
- Status reports semantic readiness (`SDXL starter · ready`) only after the JSON is actually readable.
- Added `lk comfy repair` to validate/repair the workflow pointer without knowing a JSON path.
- Managed Comfy install is now included in local model discovery/status.
- Model inventory scans nested model-family folders at bounded depth.
- Fixes the confusing state where `lk comfy` printed a workflow path while generation still said no workflow was configured.

## 2.6.2 — Comfy discovery/config polish

- Fix empty Comfy workflow configuration resolving to `.` and producing `Errno 21: Is a directory`.
- Missing workflow now reports a clean, actionable configuration message.
- Deepen old-model discovery inside recognized checkpoint / diffusion-model roots by up to three subdirectory levels.
- This catches older collections organized by model family under Comfy/A1111 folders on mounted drives.
- Working Linux generation path is otherwise unchanged.
- Future Crash remains 1.1.10.

## 2.6.1 — Living Memory metabolism

- Treat `sidebar`, `no need to remember this`, `just for now`, and equivalent language as conversation-local: RECENT retains it, candidate/durable extraction does not.
- Candidate extraction is intentionally a little more permissive for reusable choices, patterns, project decisions, and working conventions; candidates remain cheap hypotheses.
- Add visible lifecycle telemetry for local-only suppression, semantic merges, promotion, expiration, eviction, and compilation.
- Retire the permanent legacy-memory display. Existing schema-2 compact legacy content is migrated once into the current durable atom/domain system when useful, then the legacy field is cleared.
- Preserve semantic candidate merge counts and decay expiration counts across sessions.
- Future Crash remains 1.1.10.

## 2.6.0 — GPU workstation bootstrap

- Linux + NVIDIA installs now offer a first-class ComfyUI workstation setup during `install.sh`.
- Discovery happens before installation and scans HOME plus common mounted-drive roots (`/mnt`, `/media/$USER`, `/run/media/$USER`) at bounded depth.
- Detects old ComfyUI installs, A1111/Forge roots, checkpoint/diffusion directories, and large model files.
- Managed ComfyUI installs into `~/.local/share/look/services/comfyui/` with its own virtual environment.
- NVIDIA dependencies follow ComfyUI's current manual-install path; Comfy requirements and built-in Manager requirements are installed into the isolated environment.
- Managed launcher `~/.local/bin/look-comfy` binds Comfy to localhost and enables Manager.
- Existing model libraries can be reused through generated `extra_model_paths.yaml`; large files are not copied.
- Loose checkpoint/diffusion directories on mounted drives are reused only when their directory type is unambiguous.
- Starter model menu: reuse existing only; SDXL 1.0 base (~6.9 GB); FLUX.1 Schnell FP8 (~17.2 GB); both; or skip.
- Large model downloads are explicit, resumable, and SHA-256 verified.
- SDXL starter installs a packaged API-format workflow and configures LOOK so `lk generate ...` works immediately after Comfy starts.
- FLUX.1 Schnell FP8 is available as a modern optional checkpoint without pretending the SDXL workflow applies to it.
- `lk comfy start|stop|restart|discover|bootstrap` manages or revisits the setup.
- `lk generate` auto-starts a managed local Comfy service when possible.
- Installer retains the bootstrap helper and starter workflow so setup can be rerun later.
- Future Crash remains 1.1.10.

## 2.5.2 — Persistent UNSAFE consent

- Persistent `unsafe` access now asks once when the user selects that profile.
- Subsequent LO launches honor the saved UNSAFE profile without repeating the launch confirmation.
- Explicit ad-hoc `lo --unsafe` escalation still asks for session confirmation.
- UNSAFE continues to cover both filesystem tools and shell commands from 2.5.1.

## 2.5.1 — UNSAFE filesystem authority

- Fixed contradictory permission behavior in LO UNSAFE sessions.
- UNSAFE now applies to LOOK filesystem tools as well as shell commands.
- Once the user accepts the UNSAFE session warning, filesystem reads/writes/moves outside the starting workspace no longer trigger per-path access prompts.
- WORKSPACE and POWER retain the existing path-grant boundary and native access UI.
- Filesystem profile state is transaction-scoped and restored after every tool call, preventing privilege leakage between sessions/operations.

## 2.5.0 — Vision, generative media, and scheduler

- Native vision input for Ollama models that advertise `vision`.
- `lk vision IMAGE [QUESTION]` performs a direct one-shot image analysis.
- LO automatically attaches explicit local image paths in normal chat when the selected model supports vision.
- Added optional ComfyUI integration for local image generation; Comfy is discovered/configured but is never a mandatory dependency.
- `lk comfy discover` searches standard locations for older ComfyUI installs and checkpoint/model folders.
- `lk comfy host`, `workflow`, `output`, and `preview` configure the media edge.
- `lk generate PROMPT` submits a configured API-format Comfy workflow, saves outputs under `~/Pictures/LOOK` by default, and previews the first result.
- Workflow JSON supports `__PROMPT__`, `__NEGATIVE__`, and `__SEED__` placeholders.
- LO gets a host-owned `generate_image` tool; models do not invent Comfy commands.
- Added persistent LOOK scheduler owned by the resident Living AI service.
- `lk schedule in 30m`, `every 2h`, and `daily 08:00` create delayed/recurring LO background jobs.
- LO gets `schedule_prompt` and `schedule_list` tools.
- Scheduler dispatches into the existing LO job queue, preserving access profile/workspace receipts and foreground priority.
- Settings control room now exposes Vision, Image generation, and Scheduler.
- Doctor reports vision capability, Comfy availability/workflow state, and active schedules.
- Installer does not auto-download large image checkpoints; discovery/setup stays explicit.

## 2.4.0 — Settings control room

- `lk settings` is now a search-first terminal control room rather than a flat settings picker.
- Type ordinary concepts such as `memory`, `video`, `GPU`, `safe`, `sound`, `downloads`, or `shortcuts` to find the relevant control.
- `lk settings SEARCH` opens with that search already applied.
- Every setting carries plain-English explanatory text and search vocabulary; the highlighted row gets a wrapped preview pane before the user changes anything.
- Added an at-a-glance status strip for selected model, access profile, Living Memory state, and shortcut policy.
- Expanded the control room to 20 useful settings/actions across AI, MEMORY, FILES, DESKTOP, REMOTE, FEEL, PROFILE, and SYSTEM.
- Added direct control-room access to model benchmark, AI/GPU performance telemetry, Living Memory inspection/compaction, Doctor, and versions.
- File grants now have a small interactive submenu for personal folders, add/remove/list/clear.
- Preferred desktop apps now have an interactive category picker and simple app-name/path entry.
- Shortcut policy can now be changed directly inside settings.
- Direct `lk ...` commands remain canonical and call the same underlying settings machinery.
- Noninteractive `lk settings` still prints a complete readable settings report.

## 2.3.9 — Model runtime-fit benchmark

- `lk ollama test` now grades interactive runtime fit separately from model capability.
- Adds EXCELLENT / GOOD / SLOW / POOR runtime labels using broad TTFT and generation-rate thresholds.
- Pathological warm performance now produces an explicit note pointing to `lk ai stats` and `ollama ps`.
- Benchmark ranking prefers models that are both capable and practically responsive.
- Runtime classification deliberately does not claim GPU spill from timing alone.
- Documentation/help reviewed after the 2.3.8 shell-namespace cleanup.

## 2.3.8 — Polite shell namespace

- LOOK now treats `lk` as the canonical namespace and adds collision-resistant fast commands:
  `lkl` detail, `lkd` directories, `lkf` files, `lkt` tree, `lkr` recent, `lkz` size.
- Canonical forms remain `lk detail`, `lk dirs`, `lk files`, `lk tree`, `lk recent`, and `lk size`.
- LOOK no longer shadows the canonical Unix `ls` command.
- Historical `lsd`, `lsf`, and `lc` convenience aliases are no longer installed.
- Ultra-short `l`, `ll`, `ld`, `lf`, `lt`, `lr`, and `lz` are now opportunistic conveniences rather than assumed global vocabulary.
- In default `polite` mode, an existing alias, function, builtin, or executable wins.
- `lk shortcuts force` may replace existing aliases/functions after `rb`, but LOOK still refuses to shadow builtins or real executables such as `ld`, `ls`, or an installed `lf`.
- `lk shortcuts` documents the canonical, fast, and optional layers and reports executable collisions visible to LOOK.
- Existing `fc` protection remains unchanged: native Zsh owns `fc`; Future Crash uses `fcr`, `rst`, or `future-crash`.

## 2.3.7 — Stop shadowing Zsh `fc`

- Removed LOOK's dual-purpose `fc` wrapper entirely.
- `fc` is now permanently left to native Zsh history/editor behavior.
- Future Crash launchers are `fcr`, `rst`, and `future-crash`.
- This avoids shell/plugin/history edge cases around `fc` and prevents pasted/history activity from ever reaching Future Crash through that name.

## 2.3.6 — Dual-purpose `fc`

- Restores the convenient `fc` Future Crash launcher without breaking Zsh history.
- `fc` with no arguments launches Future Crash.
- `fc` with any arguments delegates verbatim to Zsh's native `builtin fc`.
- This preserves shell/plugin calls such as `fc -p -a /dev/null 0 0` while keeping the original shortcut UX.
- `fcr`, `rst`, and `future-crash` remain valid launchers.

## 2.3.5 — Restore Zsh `fc`

- Fixed a shell-integration collision that could launch Future Crash unexpectedly during paste/history activity.
- LOOK had defined `fc` as a Future Crash shortcut, but `fc` is a native Zsh history builtin used internally by shells/plugins.
- Calls such as `fc -p -a /dev/null 0 0` were therefore being forwarded into `future_crash.py`, producing bogus argparse errors.
- The installer/profile now explicitly removes any stale LOOK `fc` function and restores the native Zsh builtin.
- The short Future Crash launcher is now `fcr`; `rst` and `future-crash` remain unchanged.
- Future Crash's argument parser remains strict; the bug was in the caller, not the parser.

## 2.3.4 — Selected-model benchmark fix

- `lk ollama test` now benchmarks the model selected in LOOK, not whichever Ollama model happens to be resident.
- Switching models in `lk ollama models` is now reflected immediately by the next single-model benchmark.
- If the selected model is not installed on the active host, the benchmark reports that directly instead of silently testing another resident model.
- `lk ollama test --all` behavior is unchanged.
- Future Crash remains 1.1.10.

## 2.3.3 — Agent cleanup + desktop bridge

- Models that explicitly lack Ollama tool support no longer receive tool schemas, preventing `HTTP 400 Bad Request` on models such as DeepSeek-R1; LO remains usable for normal chat/thinking and host-side safe inspection repair.
- After LOOK repairs a prose-only safe inspection, the next model turn is final-answer-only with tools disabled, preventing redundant `which ...` / repeated inspection loops.
- Activity/result presentation is separated cleanly so spinners do not collide with `inspect ›` or result text.
- Compact thinking redraw now uses the previous rolling-window height and actual terminal width, fixing duplicated/concatenated lines after the three-line window fills.
- Added host-owned desktop bridge tools and commands: `open_path`, `preview_path`, `reveal_path`, `lk open`, `lk preview`, `lk reveal`.
- Added `lk apps` preferred-app registry for browser/editor/image/pdf/video/audio. OS defaults remain the default; overrides are optional.
- macOS preview uses Quick Look when available; Linux defaults to `xdg-open`; Windows uses the system association. Preferred apps such as VLC/mpv can override a category.
- Desktop bridge respects LO read/path grants when invoked by the model.
- `lk doctor`, help, settings, command index, and completions now describe desktop bridge availability/preferences.
- No new mandatory GUI/media dependency is installed; system defaults are preferred and optional helpers are detected.
- Future Crash remains 1.1.10; Living Memory remains schema 3.

## 2.3.2 — Native command authority + model interaction repair

- POWER command permission is now owned by LOOK's native terminal UI, never negotiated conversationally by the model.
- Reusable command confirmation: `[y] once · [s] allow command this session · Enter/Esc cancel`.
- Session grants authorize the exact normalized command only, never every invocation of an executable.
- Known read-only inspections auto-run in POWER without confirmation: common `--version`/`--help`, Ollama list/ps/show/version, Git status/log/diff/show/branch/rev-parse/remote, nvidia-smi, and basic OS inspection commands.
- Shell composition/redirection and mutating command forms remain outside the inspection allowlist.
- Shell command subprocesses now use DEVNULL stdin, preventing child processes from competing with LO for the interactive terminal.
- Added one-shot agent repair: when a capable model explains a known-safe inspection instead of calling the tool, LOOK may execute the inspection deterministically and feed the result back for a final answer.
- Fixed compact thinking renderer emitting literal `\r` / `\033` text instead of actual terminal control sequences, exposed clearly by gpt-oss.
- `lo` natural-language invocation now carries `nocorrect`, preventing Zsh from trying to change words such as `version` to a local `VERSION` filename.
- `lk ollama test` now reports AGENT separately from TOOLS: schema/tool judgment and natural tool execution are distinct capabilities.
- Future Crash remains 1.1.10; Living Memory schema remains 3.

## 2.3.1 — Query-aware memory startup fix

- Fixed LO startup crash in 2.3.0: memory retrieval referenced `prompt` before the first prompt had been assigned.
- Memory now occupies one stable system-message slot and is refreshed against the current user prompt immediately before every inference turn.
- The memory file is reloaded between turns, so background Living Memory updates can become visible during a long-running LO session.
- Relevant memory snapshots no longer accumulate in chat history.
- No memory schema, permissions, file tools, or Future Crash behavior changed.

## 2.3.0 — Living Memory compiler

- Living Memory schema 3 separates cheap candidates from durable atomic memory.
- Durable memory is classified into compact semantic domains: PERSONAL, PREFERENCES, PROJECTS, STYLE, GENERAL.
- Background compiler rewrites domain summaries and a tiny core routing summary, aggressively minimizing words while preserving scope and uncertainty.
- Old schema-2 long-term summary text is preserved as LEGACY (inactive) evidence rather than automatically injected into prompts.
- Candidate admission is more permissive; candidate slots are competitive by importance, reinforcement, and recency.
- Machine/runtime facts are excluded from autobiographical memory.
- Prompt retrieval is relevance-driven: compact core + relevant domain summaries + up to six relevant durable atoms + four relevant candidates.
- Idle Living AI uses free cycles for memory recompilation at most once every six hours.
- Added `lk memory compact` / `compile`.
- `lk memory` now exposes core summary, domains, durable atoms, candidate ecology, promotions, evictions, and compiler timing.
- Full help/commands/settings/completions audit for access grants, undo history, filer keys, terminal ownership, memory compiler, AI stats, and current profiles.
- Future Crash remains 1.1.10.

## 2.2.3 — Receipts are reality

- File creation receipts now include canonical absolute paths, so the model no longer has to infer where a successful write occurred.
- Single-file writes now return `WRITE OK · <absolute path>`.
- LO treats filesystem receipts as ground truth and is explicitly forbidden from contradicting a successful receipt with stale conversation/memory.
- Host mutation detection now distinguishes new execution requests from retrospective discussion, questions, acknowledgements, and feedback.
- Fixes follow-up turns such as “you did make it in the correct ~/Downloads folder” being rewritten into “I did not execute a filesystem mutation tool.”
- Future Crash child-shell mode now has its own terminal title: `◌ FUTURE CRASH · SHELL · <folder>`.
- Returning from that child shell restores `● FUTURE CRASH`; ordinary shell remains `LOOK · <folder>`.

## 2.2.2 — Zsh reload compatibility

- Fixed `rb` / shell reload parse failure when aliases from an older LOOK session were still active.
- The generated LOOK Zsh profile now unaliases `lk`, `lo`, `fc`, `rst`, and `commands` before parsing same-name function definitions.
- This specifically fixes `defining function based on alias 'lk'` / `parse error near '()'` during Zsh initialization.
- No runtime, permission, memory, AI, or filesystem behavior changed.

## 2.2.1 — Permissioned filesystem reach

- The LO workspace is now the default trust boundary, not a hard prison.
- Outside-workspace file tools trigger a host-owned permission prompt instead of forcing the model to improvise.
- Grants: Allow Once, Session, Always, or Personal folders.
- `lk access` inspects persistent grants; `add`, `remove`, `clear`, and `personal` manage them.
- Permanent grants are stored locally in LOOK state with mode 0600.
- Write grants include read access; read-only grants remain available.
- Allow Once lasts for exactly one complete filesystem tool transaction.
- Background/non-interactive work fails closed instead of inventing permission.
- Named destinations remain exact: denial never falls back to the current directory.
- Future Crash remains 1.1.9.

## 2.2.0 — Terminal ownership + undo journal

- Terminal/tab titles now identify the active surface: `● LOOK`, `● LO`, and `● FUTURE CRASH`, returning to `LOOK · <folder>` at the shell.
- Added `lk undo list` with READY/BLOCKED classification and reasons.
- Added `lk undo skip`: explicitly abandon only the newest BLOCKED record, making older history reachable without touching the filesystem.
- Ordinary `lk undo` remains strict and never auto-skips divergent history.
- Fixed false-success mutation reporting: failed filesystem tools can no longer be followed by prose claiming a file was created/moved/copied.
- Common named home folders (`Downloads`, `Desktop`, `Documents`) are normalized to their canonical `~/...` destinations for file creation; workspace boundaries still apply.
- Includes 2.1.10 destination fidelity, reveal tool, deterministic `cd`/zoxide split, and 2.1.9 warm-model fixes.

## 2.1.10 — File destination fidelity

- Fixed `copy_path` / `move_path` crash caused by missing `_final_destination`.
- Named destination folders are now an explicit LO execution contract: `in Downloads` must produce a path containing `Downloads`, never silently fall back to the current directory.
- If a requested destination is outside the current WORKSPACE boundary, LO must report the boundary instead of claiming success elsewhere.
- Added `reveal_path` tool for “show me this file” / Finder / host file-manager requests.
- Added direct `lk reveal PATH`; no new short alias.
- Filesystem-tool programming errors are contained inside the tool boundary instead of crashing the LO session.
- Installer shell profile now keeps real `cd` deterministic; zoxide remains on `z`, fixing newly extracted directories that zoxide has never indexed.
- No memory, broker, model, or performance-policy changes.

## 2.1.9 — Ollama keep-alive compatibility fix

- Fixed interactive LO requests sending permanent residency as the string `"-1"`.
- Ollama now receives numeric `keep_alive: -1`, which preserves permanent model residency without triggering HTTP 400 on stricter Ollama builds.
- No other behavior changed.

## 2.1.8 — Warm model residency

- Normal interactive LO chat now requests Ollama `keep_alive=-1` so the selected primary model stays resident instead of paying repeated cold-load penalties.
- `lk ai stats` now labels the last task as warm/cold using Ollama load duration.
- Rolling stats show warm vs cold task counts.
- `/api/ps` display now distinguishes GPU-resident model bytes from model size; it no longer mislabels model size as physical VRAM capacity.
- No model choice, thinking policy, tool behavior, memory policy, or Future Crash behavior changes.

## 2.1.7 — Input polish + AI performance telemetry

- Filer footer now distinguishes Clipboard from Copy To and orders clipboard before destination mutations.
- Shift-Tab marks exactly like Tab.
- Left arrow navigates to parent; right arrow follows Enter/open semantics.
- Added restrained activity indicators for first-model-token waits, blocking file mutations, commands, and global catalog scans.
- Added `lk ai stats`: rolling wall time, inference rounds, tool calls, prompt eval, generation speed, load time, Ollama VRAM allocation/context, and local NVIDIA detail when applicable.
- LO telemetry stores timing/count data only; no prompts or response content.
- AI control surface now exposes thinking effort and thinking-display separately.
- No Living Memory policy or Future Crash behavior changes.

## 2.1.6 — Living AI liveness hardening

- Broker singleton detection now trusts the Unix socket protocol, not PID existence alone.
- Stale/reused PID files can no longer block Living AI startup.
- Unexpected background-processing exceptions are contained and logged instead of killing the resident broker.
- Background LO job exceptions are contained.
- `lk memory` now self-heals when durable memory work exists but Living AI is stopped.
- Memory policy and Future Crash behavior are unchanged.

## 2.1.5 — Living AI version handshake

- Living AI now reports the LOOK core version it imported at startup.
- LOOK compares the resident broker core version with the installed LOOK version before waking background work.
- A stale broker from a prior upgrade is gracefully stopped and replaced before queued memory/jobs are processed.
- `lk ai status` shows the running core version and warns when a restart is pending.
- No memory policy, Future Crash personality, or scheduler-priority changes.

## 2.1.4 — Living Memory reinforcement correctness

- Repeated semantically equivalent candidate evidence now increments USES and importance.
- Strong overlap with an existing candidate can count as reinforcement even when the extractor returns NONE.
- Post-hoc duplicate consolidation now accumulates evidence instead of discarding repeat mentions with max(uses).
- Added persistent extraction and consolidation receipts to `lk memory`.
- Broker, scheduler, Future Crash, and inference coordination are unchanged.

## 2.1.3 — Living Memory observability + evidence fallback

- Fixed a practical Living Memory failure mode where RECENT advanced and the durable queue drained, but candidate extraction could return `NONE` indefinitely.
- Added a deterministic fallback for obvious user preferences, working conventions, explicit memory language, and ongoing project-state statements.
- Model extraction remains the primary path; the fallback only catches clear evidence when the model is too conservative.
- Added extraction counters and last-extraction receipts to `lk memory`.
- `lk memory` now distinguishes `candidate:model`, `candidate:obvious`, `candidate:explicit`, and `none`.
- Worker errors are surfaced directly in the memory status view.
- Living AI scheduling, memory schema 2, Future Crash 1.1.8, and all 2.1.2 inference coordination remain unchanged.

## 2.1.2 — Shared inference coordination

- Living AI now exposes permit/lease coordination for independent AI clients.
- Future Crash explicit Ask/Workstation requests register interactive inference leases.
- Automatic Future Crash Oracle work yields to LO foreground work and queued Living AI maintenance.
- Future Crash and LO remain separate personality, memory, permission, and tool domains.
- Standalone Future Crash behavior is preserved when the broker is absent.

## 2.1.1 — Living AI release hardening

- `lk ai status` now returns success for both running and stopped states; status is inspection, not a health assertion.
- Synchronized canonical README/version metadata with 2.1.1 / LOOK 4.1.1 / Future Crash 1.1.7.
- Updated LOOK information user-agent version.
- Revalidated Living AI broker, Living Memory policy, documentation inventory, installer metadata, completions, and archive integrity.

## 2.1.0 — Living AI

- Added `look_ai.py`, a resident local AI broker using a private Unix-domain socket.
- Shell startup launches the broker silently; AI-producing commands also lazily start it if needed.
- Durable filesystem queues remain the source of truth: the socket is the fast coordinator, not the persistence layer.
- Broker priority: foreground interactive work blocks new background starts; explicit `lo bg` jobs outrank memory/skill housekeeping.
- Background work is processed one unit at a time so foreground interaction can win between model calls.
- Added `lk ai [status|start|stop|wake]`.
- Replaced per-conversation memory decay with elapsed-time decay.
- Candidate extraction now semantically matches new observations against active candidates and the long-term summary.
- Repeated semantic matches reinforce importance/uses instead of creating paraphrased duplicates.
- Long-term consolidation is event-driven by durable/repeated evidence, not modulo-six conversation counts.
- Successfully consolidated candidates leave the active pool, freeing room for new observations.
- `lk memory` now shows importance/uses, broker state, queue depth, and last maintenance age.
- Recent continuity still stores both user and assistant sides while displaying the user side compactly.
- Memory schema advances to v2 with maintenance/evidence timestamps.
- Memory queue consumption now preflights Ollama reachability; unavailable inference leaves durable jobs intact.
- Resident broker backs off after maintenance failures instead of tight-loop retrying.
- Future Crash remains 1.1.7.

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
