# Future Crash + LOOK — Code Health

The project now carries a small dependency-free structural audit:

```bash
python3 tools/code_health.py
python3 tools/code_health.py --check
./tools/verify.sh
```

`code_health.py` is deliberately not a style linter. It measures the things that have
actually caused maintenance trouble here: concentration of code in giant traffic
intersections, shadowed definitions, stale interaction states, and tests coupled to
literal source spelling.

## Current structural snapshot

- Python production parses cleanly.
- Duplicate definitions: **0**.
- LOOK pager interaction model: **Browse ↔ Filter only**. The old `cursoring` and
  `selecting` states are gone, not merely unreachable.
- `pager()` is roughly **510 lines**, down by about 180 lines after removing the dead
  SELECT/cursor machinery.
- The largest remaining concentration is `look/lk::ollama_chat()` (~1,500 lines),
  followed by `core/node.py::main()` and LOOK's pager.
- A large fraction of the historical regression suite still inspects source text.
  Existing contracts are retained where useful, but new tests should prefer public
  behavior or stable function boundaries over exact implementation spelling.

## Verification policy

A release is healthy only if `./tools/verify.sh` succeeds. It checks:

1. Structural invariants (`code_health.py --check`).
2. Python compilation, including the extensionless `look/lk` executable.
3. Installer shell syntax.
4. Signal Window JavaScript syntax when Node is available.
5. The complete pytest regression suite.

The structural check intentionally fails on duplicate definitions, Python parse errors,
or resurrection of the legacy LOOK `cursoring` / `selecting` states.

## Refactoring rule

Do not split modules merely to make line counts smaller. Extract only when a boundary
has a name and one job. Current highest-value future boundaries are:

- LO/Ollama conversation orchestration out of `look/lk::ollama_chat()`.
- Unified Node command dispatch out of `core/node.py::main()`.
- LOOK pager rendering and key-to-intent translation, once behavior tests cover those
  boundaries independently.

The goal is not fashionable architecture. The goal is to make any behavior have one
obvious home and one obvious test.

## First LO extraction

The post-8.9.0 [response-stream audit](AUDIT_LO_STREAM.md) extracts normalized
stream assembly to `look/lo_stream.py`. Fabric and direct Ollama share that
boundary; terminal cleanup and action/receipt policy remain in the conversation
loop. `ollama_chat()` is now 1,495 lines with structural complexity 483, down
from 1,515 / 501. The next audit should trace final-response truth through saved
conversation and memory before extracting more policy.
