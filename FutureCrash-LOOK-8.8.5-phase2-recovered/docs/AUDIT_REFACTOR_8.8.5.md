# Future Crash + LOOK 8.8.5 — Maximal Code-Health Audit and Cleanup

## Scope

This pass began as a read-only audit after the LOOK browse-arrow bug exposed a hidden legacy state machine. It then became a bounded cleanup: remove proven dead state, make installation self-verifying, make the regression suite truthful, and add repeatable structural measurements. It deliberately does **not** perform speculative architecture rewrites of working subsystems.

## Executive result

The repository is structurally healthier than the bug initially suggested. Debt is concentrated in a few traffic intersections rather than spread uniformly across the project. The Fabric core already has useful module boundaries; LOOK and the top-level command/HTTP dispatch surfaces carry most of the cognitive load.

The cleaned tree finishes with:

- **733 passing tests, 0 failures** from an ordinary repository-root `pytest` run.
- A one-command release gate: `./tools/verify.sh`.
- Clean Python compilation, installer shell syntax, and Signal Window JavaScript syntax.
- **0 duplicate Python definitions** detected by the structural audit.
- LOOK pager reduced to a truthful **Browse ↔ Filter** interaction model.
- Immediate byte-for-byte verification for installed LOOK runtime files.
- Final unified-installer verification now includes `look_renderer.py`.

## Before / after

| Metric | Uploaded baseline | Cleaned tree | Change |
| --- | ---: | ---: | ---: |
| Production files | 40 | 40 | — |
| Production lines | 45,642 | 45,464 | -178 |
| Production code lines | 40,038 | 39,866 | -172 |
| Functions | 1,941 | 1,941 | — |
| Classes | 59 | 59 | — |
| Test files | 188 | 180 | -8 net |
| Source-contract test files | 150 | 144 | -6 |
| Duplicate definitions | 1 | 0 | fixed |
| Legacy LOOK pager states | `cursoring`, `selecting` | none | removed |
| `pager()` length | 694 | 510 | -184 (-26.5%) |
| `pager()` structural complexity | 315 | 177 | -138 (-43.8%) |
| Regression result | 722 pass / 37 fail | 733 pass / 0 fail | green |

The line-count reduction is intentionally modest. This was not a line-deletion contest; only code with a defensible reason to disappear was removed.

## What was wrong with LOOK

The arrow-navigation bug exposed three overlapping concepts in `pager()`:

1. ordinary browse,
2. FILTER/focus,
3. legacy `cursoring` / SELECT behavior.

The source fix made browse arrows enter FILTER, but the old SELECT machinery remained in the renderer even after no path could set `cursoring=True`. The program therefore still *described* a feature that no longer existed. That made code search and debugging misleading.

This cleanup removes `cursoring` and `selecting` as states rather than merely making them unreachable. Initial selection uses FILTER focus, and browse arrows enter FILTER directly. Esc from FILTER now explicitly restores the browse grid, clears focus/matches, and resets the viewport rather than leaving internal and rendered state capable of disagreeing.

A functional regression test now exercises that state transition through the pager instead of merely asserting source strings.

## Installer integrity

The stale-renderer incident had a concrete cause in the deployment safety net: `install-look.sh` copied `look_renderer.py`, but the unified installer's final byte-comparison list omitted it.

Two defenses now exist:

1. `install-look.sh` routes managed runtime files through one `install_file` primitive that copies and immediately verifies source and destination with `cmp`.
2. `install.sh` performs final release-boundary verification and includes `look_renderer.py` alongside the other LOOK runtime modules.

This makes the desired invariant explicit: a successful installer cannot silently leave a stale managed runtime file behind.

## Test-suite repair

The test suite was a major strength—hundreds of focused regressions—but part of it had become a historical archive of implementation spellings. The baseline produced 37 failures once invoked with the environment it expected. Some failures literally required the old `cursoring=bool(matches)` behavior that had just been intentionally removed; others asserted superseded preview internals.

The cleanup:

- adds `pytest.ini`, so repository-root pytest no longer depends on hidden `PYTHONPATH=.` knowledge;
- retains current behavioral coverage;
- rewrites LOOK state tests around the real Browse ↔ Filter contract;
- updates current source-contract tests where terminology changed;
- removes superseded historical implementation-contract tests where newer tests already cover the replacement behavior;
- adds installer-integrity and structural-health regression tests.

No tests are skipped to manufacture a green result.

## Other correctness cleanup

### Duplicate `ModelRegistry.snapshot()`

`core/node.py` contained two definitions of the same method; the first was silently shadowed by the second. The dead definition is removed, leaving the intended nonblocking cached snapshot implementation.

### Legacy media catalog identity

Older catalog rows may lack an explicit media `id`. `_local_media_catalog()` and `_local_media_entry()` now derive the same stable path-based identifier used by `look/media_core.py`, preserving backward compatibility without widening path access outside the catalog boundary.

## New maintainability tools

### `tools/code_health.py`

A dependency-free structural audit aimed at problems that have actually hurt this project. It reports:

- production/test size,
- largest modules and functions,
- conservative branch complexity,
- duplicate definitions,
- source-reading/source-contract test load,
- legacy LOOK pager states,
- broad exception catches as an informational edge-safety metric.

`python3 tools/code_health.py --check` fails on parse errors, duplicate definitions, or resurrection of the removed LOOK pager states.

### `tools/verify.sh`

The release gate runs:

1. structural health checks,
2. Python compilation,
3. installer shell syntax,
4. Signal Window JavaScript syntax when Node is available,
5. the full pytest suite.

Current result: **733 passed — VERIFY OK**.

## Remaining concentration: measured, not hidden

The cleanup intentionally leaves the following large intersections for later behavior-preserving extraction:

| Function | Approx. lines | Structural complexity |
| --- | ---: | ---: |
| `look/lk::ollama_chat()` | 1,515 | 501 |
| `core/node.py::main()` | 575 | 377 |
| `look/lk::main()` | 329 | 221 |
| `core/node.py::API.do_POST()` | 282 | 202 |
| `look/look_renderer.py::pager()` | 510 | 177 |
| `signal-window/server.py::App.do_POST()` | 250 | 134 |

These are the next rational targets because they concentrate decisions and responsibilities. They should be split only after stable behavior seams are established; moving 1,500 lines into arbitrary smaller files would improve a metric without improving the program.

The code-health report also counts **462 broad exception catches**. That number is intentionally informational, not a failure condition: this is an edge-heavy local-first system where filesystem, subprocess, network, optional-device, and terminal failures often should degrade gracefully. Future work should audit them by boundary and observability rather than mechanically replacing every broad catch.

## Architectural verdict

**No rewrite.**

Future Crash + LOOK has a viable architecture. The Fabric subsystem in particular already separates identity, packets, cognition, memory, state, transport, and related concerns into reasonably scoped modules. The project’s main risk is not generalized poor code; it is accumulated behavior at a few central dispatch/state-machine functions plus tests that occasionally preserve obsolete implementation history.

The maintenance rule going forward should be:

> One concept, one obvious home, one observable contract, one useful test.

And the release rule should be:

```bash
./tools/verify.sh
```

If that does not end in `VERIFY OK`, the release is not finished.
