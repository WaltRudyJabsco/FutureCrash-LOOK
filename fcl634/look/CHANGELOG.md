## 6.3.4 — Saved Means Saved

- Albert Saved entries are durable snapshots that can be reopened onto the live paper after the original fold is dismissed.
- Saved entries now expose `open on paper` and `remove saved` instead of dead live-fold controls.
- Reopened audio folds recreate their player and visualizer normally.

## 6.3.3 — Alive

- Albert now loads the shared native LO engine directly instead of calling Signal's paired-browser `/api/chat` endpoint. Signal can be closed; Albert cognition remains available as long as LOOK/LO is installed.
- Albert keeps its own bounded session history so follow-ups retain context through the shared cognition plane.
- Albert audio folds gain a small live EQ: a real Web Audio analyser for safe local/same-origin audio, with a playback-synchronized fallback for cross-origin streams. Video folds deliberately remain clean.
- `lk player` gains a small audio-only playback visualizer. It never appears for video and is explicitly presentation, not fabricated frequency telemetry.

## 6.3.2 — One Brain

- Albert no longer terminates unknown requests with a fake “understood” cognition receipt.
- Non-fast-path requests now hand off to the shared native LO cognition/tool plane used by Signal.
- Albert persists a browser session id, so follow-ups such as “what was the weather?” retain the active location/context.
- If shared cognition is unavailable, Albert fails closed and says nothing was executed.

# 5.4.7

- Filter beacon/light/RGB/pulse renderer effects out of Dash RECENT.
- Consume terminal ANSI escape sequences before single-key Dash command dispatch so scrolling/arrows cannot trigger beacon.
- Rate-limit the beacon hotkey while a diagnostic show is in flight.
- Harden Signal browser media handoff and stream proxied audio incrementally.

# 5.4.6

- Promote mpv to the normal workstation dependency set so upgrades make Macs playback-ready by default.
- Preserve node-scoped queue/session semantics while exposing browser-safe audio bytes through Fabric.
- Report playback readiness separately from queue/control availability.

# 5.4.5

- Add node-scoped Fabric media output discovery and remote deterministic media control.
- Add full MediaSession export/adopt path used for queue-preserving output handoff.
- Add `lk media outputs` and `lk media on NODE ...`.
- Document node-scoped sessions and Signal output routing.

# 5.4.4

- Discover mpv reliably from background-service environments, including Linuxbrew/Homebrew paths.
- Return concrete playback-edge diagnostics through LO media tool failures.
- Preserve artifact-backed vision routing for browser camera/image resources.

# 5.3.0 — Decision Plane

- Adds renderer-neutral Fabric DecisionRequests with confidence, consequence, reversibility, deadline, preferred choice, and timeout policy.
- Adds non-blocking deadline semantics: Power/Unsafe may continue low-risk reversible work; Workspace/Conservative defer; consequential/irreversible work cancels without explicit confirmation.
- Adds Fabric-wide decision discovery and answering plus Signal one-tap decision cards.
- Adds optional OpenJev-compatible shadow decisions without making the learned worker authoritative or required.
- Adds `lk fabric decisions`, `decision`, `answer`, `ask`, and `decision-shadow`.

# 5.2.19 — Media Session Reliability

- Reuse the LOOK-owned mpv process for ordinary play requests instead of spawning overlapping players.
- Add deterministic first/last/first-on-album media controls for LO.
- Make selector queue mutation canonical-only so Q returns immediately without stream resolution or player I/O.
- Preserve MediaSession as the owner of queue state; mpv remains a playback worker.

# 5.2.18 — LO Media Tools + LOOK Media Filter

- LO can search/play/queue/control Fabric media through purpose-built tools.
- Local media imperatives are host-routed before general inference/search.
- Media find/browse now follow LOOK filter behavior with Tab multi-select and uppercase contextual actions.

## 4.45.1 — Fabric media catalog + selector

- `lk media find`/`browse` now use a native LOOK selector instead of requiring exact title retyping.
- Add `lk media fabric`, `lk media identify`, and catalog-backed media completion.
- Merge online catalog rows by SHA, preserve multi-node locations, and prefer local copies.
- Preserve verified digest metadata across unchanged rescans.

## 4.45.0 — Media sessions + miniplayer

- Add a dependency-free media library/session core.
- Add fast library scanning/search, canonical queues, saved playlists, repeat, and directory/query playback.
- Add `lk player`, a tiny live terminal view over the current LOOK MediaSession.
- Keep mpv as the optional playback edge and preserve Fabric range-stream transport for remote/content-addressed media.

## 4.44.8 — Isolated per-node model qualification

- `lk ollama test --all` now benchmarks enabled models alone under identical 4096-context residency conditions and reports load time separately from warm median TTFT.
- Preserve/restore the pre-test warm set and expose node-local eligible/disabled model candidates in `lk ollama curate`.
- Coordinate with the local Unified Node benchmark guard so automatic qualification/curation and Fabric jobs cannot contaminate residency measurements.

## 4.44.7 — Adaptive model curator

- Stabilize resident-set concurrency testing with warm-up, alternating solo order, three-run medians, and a physical sanity bound.
- Add model-curator controls and purpose evidence display.
- Add canonical 4096-context warm commands for repeatable residency experiments.

## 4.44.6 — Model roles + resident-set evidence

- Model benchmarks now include three deterministic reasoning probes.
- Add `lk ollama test --resident-set` to measure useful overlap among already-resident models without changing residency.
- Fabric model telemetry exposes exact resident identities and raw purpose evidence rather than a single synthetic model score.
- Full Dash leaves a one-column right gutter so PULSE remains visible.

## 4.44.5 — Adaptive Dash geometry

- Responsive Dash now chooses by actual information fit and terminal geometry rather than height alone.
- Wide/short terminals use two-column operational telemetry instead of collapsing to near-Mini.
- Medium layouts use spare rows for additional telemetry and RECENT activity instead of leaving dead space.

## 4.44.4 — Responsive Dash + benchmark evidence

- Persist model benchmark results to `~/.local/share/look/ollama_benchmarks.json`.
- Keep live qualification and full benchmark evidence distinct.
- Surface benchmark fit/tools/agent/exact results through Fabric model observability.
- Make live Dash choose full, condensed, or compact layouts from terminal height.

## 4.44.3 — Model observability

- Dash replaces the ambiguous model asterisk with compact residency and qualification evidence.
- Fabric model inspection shows tested/untested/stale/failed state, TTFT, tok/s, and READY compliance.

## 4.44.2 — Dash polish

- Color-coded RECENT, Mini Dash, simpler controls, no Freeze/Activity toggle.

## 4.44.1 — Ambient Fabric dashboard

- `lk dash` renders meaningful Fabric state transitions as optional, restrained ambient color flashes.
- RECENT now states its observation scope, labels LOCAL/REMOTE events, and makes cross-day timestamps obvious.
- Stream/chunk noise never triggers color flashes.

## 4.43.3

- WEATHER follow-ups remain on the active typed receipt/location instead of relying on prose context.
- Daily high/low questions are answered directly from canonical daily fields.
- Weather accuracy challenges can cross-check the nearest National Weather Service observation.

# Changelog

## 4.43.2
- WEATHER location resolution now happens deterministically before model inference.
- Reuses the most recent explicit weather location from ephemeral interface history and supports operator-owned default location via `LOOK_WEATHER_LOCATION` / `LO_WEATHER_LOCATION`.
- Canonicalizes US state abbreviations for geocoding and distinguishes missing-location questions from provider failures.

## 4.43.1
- WEATHER preflight retries one transient read failure before giving up, while preserving fail-closed receipts and no blind retries for mutations.
- Dashboard Fabric light hotkeys use the daemon control plane, matching the CLI broadcast path.

- `lk fabric lights` exposes synchronized demo, disco, Christmas, pulse, RGB, and stop controls.

## 4.42.0 — Fabric Alive

- `lk fabric beacon` gives the Fabric a synchronized, visible smoke test; `b` triggers it from `lk dash`.
- LO's active inference spinner gains restrained patient status wording on genuinely long waits.
- Weather Fast Edge now uses a compact receipt-only inference payload after deterministic retrieval.
- Dashboard event polling now reads the newest bounded tail instead of eventually freezing on the oldest 128 ledger events.

## 4.9.1 — Fast Edge

- Fixes the 4.9.0 installed-runtime packaging regression by installing and verifying `core/conductor.py` beside `fabric_client.py`.
- Adds an installed-layout smoke import so a coherent source tree can no longer pass release validation while the installed Fabric runtime is incomplete.
- Current weather with an explicit location now takes a deterministic WEATHER preflight edge before inference, eliminating the wasteful "ask model to call obvious tool" round.
- Pure weather turns omit the full tool schema after a successful receipt, reducing prompt cost and allowing a text-only reflex model to phrase the result.
- Fabric telemetry now announces worker/model placement before inference and reports prompt-evaluation time separately from output evaluation.

## 4.9.0 — Reflex Conductor

- Added a zero-I/O deterministic conductor that classifies turns as reflex, balanced, or deep before placement.
- Fabric routing now combines hard capability filtering with residency, live load, measured qualification TTFT/tok-s, locality, model size, and work class.
- LO emits truthful `conductor` events and keeps the chosen worker/model sticky for the rest of the turn.
- Reflex work favors small warm models; deep/code/vision work favors capable larger models without adding an extra LLM round-trip.

## 4.40.0 — Fabric dashboard

- Adds `lk dash` as the operational cockpit over Fabric truth.
- `lk fabric dashboard` / `lk fabric dash` are aliases for the same view.
- Dashboard links to Fabric watch, settings, doctor, and confirmed managed-service restart.

## 4.39.4 — Fabric socket ownership

- Ships with Unified Node 4.7.4 control-plane socket lifecycle and accept-failure recovery.
- `lk fabric http` surfaces accept-error telemetry from the node.

## 4.39.3 — Fabric HTTP diagnostics

- `lk fabric http` now passes through to the Unified Node HTTP pressure view.
- Ships with Future Crash + LOOK 4.7.3 ingress-process isolation.

## 4.39.2 — Provenance receipts + lean Fabric routing

- Emit deterministic source receipts from the information edge that actually ran instead of relying on model prose to preserve provenance.
- Native LO event streams carry `source_receipt` metadata for browser interfaces such as Signal.
- Fabric placement reuses one atomic node snapshot per attempt and removes duplicate control-plane polling.

## 4.39.1 — Trust basis

- Refresh authoritative system-clock context on every LO turn.
- Enforce live WEATHER receipts for current/forecast weather before an answer may cross the final-response boundary.

## 4.38.5

- Fabric LO now tolerates transient control-plane route discovery timeouts instead of exposing raw urllib timeout errors.

## 4.37.1 — Machine-local model scope

- Local model selection is pinned to localhost and is no longer affected by the legacy Ollama host override.
- Remote direct-host model preferences are stored per endpoint and cannot overwrite the local fallback model.
- `ollama_model` is no longer portable profile state; old profile restores skip it.
- `lk models`/Local AI stay local, while `lk ollama models` deliberately follows the legacy direct host.

## 4.33.10

- Enforces the documented 180-second timeout on primary streamed Ollama chat requests.
- Emits `inference_cancelled` plus terminal `request_done` status in JSONL mode.
- One-shot machine cancellation exits with status 130 instead of reopening an input prompt.

## 4.33.9

- Shared inference discovery + JSONL observability.
- Fixed document continuation re-anchor state crash.

## 4.33.4 — Resource attention lifecycle

- ResourceRef handles persist while expensive image payloads become attention-sensitive.
- New images attach once; ordinary conversational follow-ups stay text-only.
- Visual follow-ups recheck the relevant image, and comparison language can revive recent images from the session resource archive.
- Successful vision observation strips image payloads before later tool rounds, avoiding repeated multimodal retries and context cost.

## 4.33.3 — Vision transport hardening

- Preserves Ollama HTTP error bodies instead of hiding the useful server diagnostic.
- Retries image turns without tools, then without thinking controls, only when Ollama returns HTTP 400.
- Keeps ResourceRef and context-governor behavior unchanged.

## 4.33.2 — Vision resources + context governor

- Image ResourceRefs now attach to vision-capable Ollama models, including Finder/desktop drops and LOOK selections.
- Resource context stays cheap: multi-file/large-document sets no longer eager-preview into the prompt.
- `read_file` supports bounded offset slices for progressive evidence gathering.
- Per-turn context governor tells LO its context/output ceiling and directs multi-document work through compact evidence cycles.
- Non-vision models report image resources without pretending to inspect them.

## 4.33.1 — Resource binding fix

- Active ResourceRef manifest is now refreshed in one stable model-facing slot.
- Explicit resource IDs are adjacent to the user intent on every turn.
- Small text resources receive bounded content previews; directories stay lazy.

## 4.33.0 — Resource Context

- Adds ResourceRef normalization for LOOK selections, CLI paths, and terminal drag/drop input.
- LO uses explicit resources directly instead of rediscovering them by filename.

## 4.32.0 — Grammar audit + command palette

- `lk` now always enters interactive LOOK on a TTY, independent of directory size.
- `lk recent/detail/dirs/files/tree/size` use the same interactive contract as their short aliases.
- `lk commands` is now searchable/selectable and can compose into the parent Zsh prompt.
- Multi-item Move/Copy validates or creates a missing destination before spawning `_batch`.

## 4.31.0 — Structured tool truth

- `_ToolResult` separates machine truth from presentation text.
- `_normalize_tool_result()` dispatches to explicit tool-family contracts.
- Generic transaction journaling consumes typed `ok/status`, not English heuristics.

## 4.30.1 — Generic mutation truth

- Mutation receipts are first-class final-response truth.
- Fixes tooling-audit profile resolver.

## 4.30.0 — Generic agent/tool boundary

- `_tool_transaction()` owns timing, execution, classification and forensic journaling.
- Repairs malformed legacy receipt separators automatically.
- `_TOOL_POLICY` makes capability access declarative.
- New tools can plug into the common harness instead of bespoke receipt plumbing.

## 4.22.0 — Typed candidates and epistemic receipts

- Resource type becomes deterministic edge metadata before model ranking.
- YouTube play/watch selects videos, not merely relevant pages.
- Action receipts express the strongest observed state and no stronger.
- Local media uses DISPATCH OK; playback remains unobserved.

## 4.21.0 — One resource/action harness

- Local path and public URL actions share the same intent → discovery → candidate → action → receipt discipline.
- Explicit web scope never falls back to local discovery; local scope never silently escalates to web.
- `open_url` opens exact search-returned URLs and produces a forensic receipt.
- Repeat/referent state can carry URLs as well as paths.

## 4.20.3 — Do not promote receipts into stronger facts

- Dispatch receipts no longer authorize unobserved runtime/playback claims.
- Human-readable rolling receipt viewer exposed through `lk receipts`.
- Truth vocabulary is capability-scoped.

## 4.20.2 — Close the receipt bypass

- Continuation language inherits the prior actionable referent.
- Host can deterministically replay known actions rather than asking the model to rediscover mechanics.
- Final renderer independently enforces receipt-gated success.

## 4.20.1 — Receipt-gated host actions

- Intention is not execution; execution is not success without a receipt.
- External-action guard mirrors the existing mutation-verification design.
- One repair turn lets capable models cross the tool boundary after premature prose.
- Python 3.14 warning cleanup.

## 4.20.0 — Referents and repeat actions

- Session-only current-action state, deliberately separate from durable memory.
- Deterministic repeat-action fast path.
- Current referent supplied to the model for conversational pronouns.
- Semantic discovery guidance discourages repeated locator calls.

## 4.19.2 — Formatter isolation

- Terminal markup is presentation-only again.
- Locator state no longer leaks into final-response rendering.
- Adds formatter regression check to architecture audit.

## 4.19.1 — Runtime hotfix

- AI pool uses the existing atomic JSON infrastructure.
- `_search_tokens` now correctly tokenizes Unicode word characters.

## 4.19.0 — Collapse discovery routing

- Personal discovery is a stable semantic scope, not a cwd-relative path.
- Explicit profile propagation into filesystem dispatch.
- Correct shell-search guard regex at both command paths.
- Architecture audit command documents executable routing contract.

## 4.18.0 — Escape the busy cycle

- Canonical locator enforced at the dispatcher and command boundary.
- POWER home search no longer asks for workspace grants.
- Expensive shell-search regression blocked.
- Shorter shell budgets and visible Ctrl-C cancellation.
- Direct `lk locator-test` diagnostic.

## 4.17.0 — Observable locator and AI pool

- Flush locator stage events while a tool is running.
- Durable host/model role map: primary, fast, background, fallback.
- No change to proven primary-model execution semantics yet.

## 4.16.0 — Adaptive locator

- Nearby discovery stays local; broad discovery uses the OS index.
- Global home recursion removed from interactive search.
- Locator reports elapsed milliseconds.

## 4.15.0 — Interactive agent contract

- Bounded one-directory listing.
- Search is discovery; listing is inspection.
- Semantic candidate evaluation and clarification are part of the agent loop.
- Ordinary personal-file reads do not prompt for workspace grants.
- Tool completion is not treated as task completion.

## 4.14.0 — Authority profiles

- Workspace is context, not permission boundary.
- Broad user-file perception is normal.
- Workspace allows journaled personal-file actions without shell.
- Power paths are no longer trapped in cwd.
- Find/open/play requests cannot trigger mutation completion enforcement.

## 4.13.1 — Progressive discovery

- Fuzzy ranked path search.
- Specialized search tools outrank shell search in power/unsafe.
- Empty successful shell results are not mistaken for task completion.
- Unsafe unscoped discovery searches the user's home.

## 4.13.0 — File search, playback, receipts, task seam

- Filename/path search no longer opens file contents.
- Explicit content search uses `rg`, skips binary data and caps file size.
- Media playback can prefer VLC or `LOOK_MEDIA_PLAYER`.
- LO actions write bounded JSONL audit receipts.
- Agent loop detects three identical repeated tool calls and stops the loop.
- Adds bounded per-task trace state as the seam for continuation checkpoints.

## 4.12.0 — Living Memory recall + scope

- Candidate extraction is deliberately higher recall.
- Metabolism/promotion carry more of the precision burden.
- Sidebar/temporary language is RECENT-only.
- Durable promotion requires stronger repeated evidence.
- Domain/core compilation has deterministic fallbacks.
- Memory reports extraction reasons and starvation.

## 4.11.1 — Doctor hotfix

- Fix undefined `active` variable in the no-model-loaded doctor branch.

## 4.11.0 — Active model contract

- One active model is canonical across LOOK/LO.
- Loaded state is telemetry, never selection.
- Remove silent fallback to arbitrary loaded models.
- Background workers inherit the active model.

## 4.10.1 — Progressive LOOK FIND

- `ff` / `fznv` become interactive immediately.
- Populate global catalog in a background thread.
- Stream fd/find results progressively instead of precomputing the entire catalog.
- Show scanning state without blocking interaction.

## 4.10.0 — Unified navigation

- `l`: live filesystem → local fuzzy → zoxide history → global LOOK fallback.
- `l <Tab>` merges live directory completion with zoxide memory.
- `ff` and `fznv` use LOOK FIND rather than an external fzf surface.
- Seed LOOK FIND directly from shell query text.
- `G` works from global results exactly as it does from local LOOK results.
- Remove unused legacy fuzzy-picker shell implementation.

## 4.9.4 — Navigation + model state

- Native `cd` restored.
- `l` remains smart/fuzzy and borrows zoxide's registered completion directly.
- Remove shell `g` / `go`; retain uppercase `G` inside LOOK.
- Rename model states to TEST / LOAD / SELECT.
- Compact model panel and make test toggles persist/redraw from disk truth.

## 4.9.3 — Navigation semantics

- Filesystem-first smart `cd` with zoxide fallback.
- Native directory completion restored for `cd`.
- Add `g` / `go` semantic navigation.
- Make uppercase `G` consistently mean GO inside LOOK.
- Lowercase `g` remains top-of-view.

## 4.9.2 — Command ownership cleanup

- `f` reliably means Future Crash in force mode.
- Fuzzy finder moves from `f` to `ff`.
- Restore native Zsh `fc` during migration from older LOOK releases.
- Eliminate startup-order overwrite between shortcut layer and fuzzy finder.

## 4.9.1 — rb hotfix

- Remove `rb` from the duplicate late `unfunction` cleanup.
- Preserve early alias/function cleanup before parsing.
- Restore `rb` after fresh install and reload.

## 4.9.0 — Shell grammar + deterministic edges

- Optional `f` Future Crash shortcut; native `fc` forever.
- `l -` toggles to previous directory.
- Safe explicit `lmk` option grammar and `--` literal-path escape.
- `lk match` glob resolver with version/time/name ranking.
- Configurable LibreTranslate-compatible translation edge.

## 4.8.3 — Shell ownership fixes

- Clear `rb` and other LOOK function names before function parsing.
- Never shadow Zsh's `fc` builtin.
- Implement force-mode `fc → fcr` as an interactive ZLE accept-line rewrite only.
- Fix bracketed-paste/history leakage into Future Crash.

## 4.8.2 — Dead-CWD recovery

- Add safe current-directory resolution throughout LOOK.
- Repair deleted shell CWDs at Zsh `precmd`.
- Repair before `rb`, LOOK, and LO entry.
- Prefer nearest surviving ancestor; fall back to home.

## 4.8.1 — Shared model truth

- Future Crash now inherits LOOK's selected model by default, matching the shared Ollama host behavior.
- Reduces remote GPU model churn and contention.

## 4.8.0 — LO typography system

- Introduce lightweight LO typography primitives.
- Compact chat header.
- Block-style YOU/LO conversation.
- Quieter rolling thinking.
- Tool/result receipt presentation.
- Preserve raw terminal responsiveness and fallback behavior.

## 4.7.5 — Shared Ollama host truth

- Future Crash consumes LOOK's selected Ollama host by default.
- No separate stale localhost assumption on client machines.

## 4.7.4 — Remote Comfy self-healing

- Discover shared Comfy services over Tailscale `:8188`.
- Auto-adopt reachable remote Comfy on clients.
- Prefer remote discovery before local start/install.
- Never recommend local Comfy bootstrap on a non-Linux/NVIDIA client.

## 4.7.3 — Documentation cleanup

- Collapse historical release-note sprawl into `docs/RELEASE-HISTORY.md`.
- Keep current release documentation standalone.
- No code-path changes.

## 4.7.2 — Future Crash navigation

- Unify `future-crash`, `rst`, `fcr`, and `fc`.
- In a Future Crash child shell, all four return to the existing session rather than attempting recursion.

## 4.7.1 — Stateful shortcut UI

- Force mode may intentionally reclaim Zsh builtin `fc`.
- Make `lh` collision-aware.
- Export live shortcut ownership from Zsh.
- Make LOOK home/glossary reflect active aliases instead of advertising unavailable shortcuts.

## 4.7.0 — Unified services

- Add persistent service registry.
- Add `lk services` and `lk share`.
- Give Ollama and Comfy separate stable HTTPS Serve ports.
- Add Mercury Writer discovery/configuration.
- Share-all only exposes running local services.
- Generalize settings share UI from Ollama-only to LOOK services.

## 4.6.3 — Workflow readiness

- Unify Comfy status and generation workflow resolution.
- Auto-repair to installed SDXL starter workflow.
- Add `lk comfy repair`.
- Include managed Comfy/model folders in status inventory.

## 4.6.2 — Comfy edge polish

- Cleanly reject an empty/non-file workflow path.
- Recursively inspect nested legacy model folders at bounded depth.
- Preserve working managed generation behavior.

## 4.6.2 — Memory lifecycle tuning

- RECENT preserves sidebars; durable extraction does not.
- Loosen candidate admission without loosening durable promotion.
- Track memory metabolism: local suppression, merges, promotions, expirations, evictions.
- Migrate and retire inactive legacy summary state.

## 4.6.2 — Managed Comfy workstation

- Add managed Comfy start/stop/restart lifecycle.
- Add deep mounted-drive discovery/bootstrap helper.
- Persist managed install metadata in Comfy config.
- Auto-start local managed Comfy on image generation.
- Add ready-to-run SDXL API workflow starter.
- Add verified SDXL / FLUX Schnell FP8 starter downloads.
- Reuse old Comfy/A1111 model libraries with external model paths rather than copying weights.

## 4.5.2 — One meaningful UNSAFE confirmation

- Move persistent UNSAFE consent to `lk ollama access unsafe` / LO access selection.
- Saved UNSAFE sessions no longer nag on every `lo` invocation.
- Explicit `--unsafe` remains a confirmed one-session override.

## 4.5.1 — Unified UNSAFE capability

- Thread active LO access profile through filesystem transactions.
- `_safe_workspace_path` bypasses path grants only when the current transaction is UNSAFE.
- WORKSPACE/POWER behavior is unchanged.
- Fixes `~/Downloads` writes being denied even after entering UNSAFE mode.

## 4.5.0 — Capability platform

- Add Ollama image input and automatic image-path attachment for vision models.
- Add optional ComfyUI discovery/config/generation bridge.
- Add persistent delayed/recurring scheduler to Living AI.
- Add LO tools for image generation and scheduling.
- Add vision/media/scheduler surfaces to settings, doctor, help, and completion.

## 4.5.0 — Search-first settings control room

- Rebuild `lk settings` around semantic search, descriptions, preview pane, and live current values.
- Add `lk settings SEARCH` prefiltered entry.
- Add memory, performance, benchmark, shortcut, desktop-app, Doctor, and version surfaces.
- Add interactive file-grant and desktop-app submenus.
- Preserve direct-command parity: control-room actions reuse existing functions and configuration files.

## 4.3.9 — Runtime-fit model testing

- Add runtime-fit classification to `lk ollama test`.
- Capability success no longer makes a 40-second-TTFT model look like an excellent LOOK choice.
- Slow/pathological results point to performance/residency diagnostics without overdiagnosing the cause.

## 4.3.8 — Polite shell namespace

- Add permanent `lk*` view shortcuts: `lkl`, `lkd`, `lkf`, `lkt`, `lkr`, `lkz`.
- Stop redefining `ls`; stop installing `lsd`, `lsf`, and `lc`.
- Make `l`, `ll`, `ld`, `lf`, `lt`, `lr`, `lz` collision-aware optional shortcuts.
- Add persisted `lk shortcuts polite|force` policy; builtins/executables always win.
- Remove startup behavior that blindly unaliased users' filesystem shortcuts.

## 4.3.7 — Native `fc` only

- Remove the compatibility dispatcher from 4.3.6.
- Never define `fc`; keep `fcr`/`rst` as Future Crash shortcuts.
- On reload, stale LOOK `fc` functions are still removed so the native builtin is exposed.

## 4.3.6 — `fc` compatibility dispatcher

- No-argument `fc` launches Future Crash.
- Argument-bearing `fc` delegates to native Zsh history.
- Fixes the 4.3.5 regression where typing bare `fc` opened the history editor.

## 4.3.5 — Zsh history compatibility

- Stop shadowing Zsh's native `fc` history builtin.
- On reload, remove any stale LOOK `fc` function left by older releases.
- Replace the Future Crash short launcher with `fcr`; keep `rst`.
- Fixes paste/history hooks accidentally invoking Future Crash with `fc -p -a /dev/null 0 0`.

## 4.3.4 — Benchmark selected model

- Single-model `lk ollama test` resolves from LOOK's persisted model selection.
- Resident Ollama models no longer override the benchmark target.
- Missing selected model on the active host now fails explicitly.

## 4.3.3 — Desktop bridge + agent-loop cleanup

- Gate Ollama tool schemas by selected-model capability.
- Final-answer-only turn after host safe-inspection repair.
- Clean spinner/result handoff.
- Stable three-line compact thinking renderer with terminal-width clipping.
- Add open/preview/reveal desktop tools and `lk apps` preferences.
- Extend help/settings/doctor/completions for desktop bridge.

## 4.3.2 — Terminal-native authority

- Native once/session confirmation for POWER shell commands.
- Known safe inspections execute without needless prompts.
- Exact-command session grants.
- Command subprocess stdin detached from LO terminal.
- Prose-only safe-inspection repair for models that reason about a tool but fail to call it.
- Fixed compact-thinking ANSI escapes.
- `nocorrect lo` natural-language shell wrapper.
- Added AGENT column to model benchmark.

## 4.3.1 — Current-prompt memory retrieval

- Fix `UnboundLocalError: prompt` introduced in 4.3.0.
- Refresh the stable memory context slot only after the current user prompt exists.
- Reload memory between turns so asynchronous compiler updates can be used by the active session.

## 4.3.0 — Living Memory compiler

- Memory schema 3: candidates → durable atoms → domain summaries → compact core.
- Relevant retrieval replaces dumping the entire memory pool into every prompt.
- More permissive candidate admission plus competitive eviction.
- Periodic idle compaction using Living AI.
- Machine/runtime state excluded from user memory.
- Schema-2 summaries preserved as inactive legacy text.
- Help, commands, settings, and Zsh completions audited to current behavior.

## 4.2.3 — Authoritative file receipts

- Canonical absolute paths in create/write receipts.
- Mutation receipts explicitly outrank conversational memory.
- Retrospective/question/feedback turns no longer trip the filesystem-execution guard.
- Future Crash child-shell aware shell title support.

## 4.2.2 — Reload-safe shell functions

- Clear stale LOOK aliases before defining `lo`, `fc`, `rst`, and related wrappers.
- Fixes Zsh alias expansion parse errors on `rb` after upgrading from alias-based releases.

## 4.2.1 — Permissioned filesystem reach

- Added explicit outside-workspace path grants: once/session/always/personal.
- Added `lk access` management surface.
- Host, not the model, owns permission decisions.
- External-path writes, reads, copies, moves, reveals and directory operations use the same boundary.
- Noninteractive/background operations fail closed when a grant is absent.

## 4.2.0 — Ownership + transaction history

- Terminal owner titles for LOOK/LO and idle shell.
- `lk undo list` and `lk undo skip`.
- READY/BLOCKED undo classification.
- Hard mutation-success receipts prevent hallucinated fallback success.
- Canonical home-folder destination normalization for Downloads/Desktop/Documents.

## 4.1.10 — Destination fidelity + reveal

- Restored actual copy/move destination resolver.
- Explicit named-folder destination contract.
- Added cross-platform `reveal_path` and `lk reveal PATH`.
- Filesystem tool failures no longer tear down LO.

## 4.1.9 — Keep-alive payload fix

- Send numeric `keep_alive: -1` for interactive Ollama chat requests.
- Fixes HTTP 400 introduced in 4.1.8 on Ollama servers that reject the string form.

## 4.1.8 — Warm primary model

- Interactive LO chat keeps the selected Ollama model resident indefinitely.
- Performance stats classify warm/cold tasks.
- Corrected VRAM/model-size labels.

## 4.1.7 — Ergonomics and observability

- Shift-Tab = Tab marking in filer.
- ← parent and → enter/open navigation.
- Clearer Clipboard / Copy To / Move To footer ordering.
- Waiting spinners on genuinely blocking operations.
- `lk ai stats` rolling performance diagnostics.
- Thinking effort and thinking-display both visible in AI surface.

## 4.1.6 — Broker liveness hardening

- Socket health is authoritative for singleton detection.
- Stale PID reuse no longer blocks broker startup.
- Serve-loop exceptions are contained.
- `lk memory` wakes durable queued work when the broker is absent.

## 4.1.5 — Resident broker refresh

- Added broker/core version handshake.
- Automatically replaces stale Living AI processes after upgrades.
- `lk ai status` exposes the runtime core version.

## 4.1.4 — Candidate reinforcement

- Equivalent memory evidence now reinforces active candidates.
- Existing-candidate overlap can rescue an extractor NONE.
- Added persistent consolidated-count diagnostics.

## 4.1.3 — Memory evidence receipts

- Living Memory no longer depends exclusively on one model extraction verdict.
- Added deterministic obvious-evidence fallback for clear preferences/project state.
- Added extraction diagnostics/counters to `lk memory`.

## 4.1.2 — Multi-client inference coordination

- Added per-process inference leases and background permit checks to Living AI.
- `lk ai status` now reports coordinated client count/labels.
- Existing LOOK foreground lease behavior remains compatible.

## 4.1.1 — Broker status semantics

- `lk ai status` returns exit code 0 when it successfully reports a stopped broker.
- Release metadata synchronized for multi-machine/Git distribution.

## 4.1.0 — Living AI broker + Living Memory

- Resident `look_ai.py` broker coordinates background LO jobs, memory, and skill reflection.
- Unix socket provides fast status/wake control; disk queues preserve crash recovery.
- Foreground leases prevent new maintenance work from starting during interactive LO turns.
- Memory uses elapsed-time decay, semantic reinforcement, event-driven consolidation, and candidate retirement after promotion.

## 4.0.3 — Learn from successful use

- Added deterministic `inspect_directory` counts/statistics.
- Added weak-supervision feedback detection and a detached skill-reflection worker.
- Added reinforced learned-skill metadata without sacrificing editable `skills.md`.
- Failed skills can weaken out of prompt attention without being silently deleted.
- Added `lk skills state`.

## 4.0.2 — Adaptive LO headroom

- LO now chooses FAST, STANDARD, or DEEP runtime ceilings per request.
- Standard filesystem inspection/counting/comparison tasks receive materially more generation and tool-call headroom.
- Deep tasks can use 24k context, 6k output, and 12 tool rounds.
- Runtime thinking and runtime capacity are separate controls.
- Added `lk budget` for inspecting classification during model tuning.

## 4.0.1 — Canonical information edges

- Added Wikidata, Crossref, and Internet Archive read-only tools.
- Unified information-tool provenance receipts.
- Taught LO the DIRECT / DERIVED / SEARCHED / MODEL distinction.
- Added human-facing Living With LOOK and information-edge documentation.

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

