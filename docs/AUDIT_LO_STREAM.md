# LO audit: response-stream boundary

Date: 2026-10-06

## Result

The first bounded extraction from `look/lk::ollama_chat()` is complete. The new
`look/lo_stream.py` owns assembly of normalized inference fragments and their
first-token/progress events. Fabric and direct Ollama use the same assembler.

This is a post-8.9.0 development change; component versions and release tags are
unchanged. It requires no new runtime dependencies.

## Boundary

The conversation loop still owns:

- selecting Fabric or direct Ollama and keeping a Fabric route across tool rounds;
- starting and stopping terminal waiting/thinking displays;
- request construction, tool execution, receipt enforcement, and final rendering;
- cumulative inference accounting, cancellation/error status, and memory updates.

The stream assembler owns:

- joining text and thinking fragments in arrival order;
- collecting tool calls into a fresh assistant message for each round;
- signaling the first nonempty text, thinking, or tool-call fragment;
- emitting progress every 16 text-bearing chunks;
- returning the last provider completion event without inventing usage data.

Exceptions propagate to the existing conversation-loop handlers. A failed or
cancelled stream does not return an apparently successful partial response.
The waiting display remains protected by the caller's `finally` block.

## Installation

`install-look.sh` copies and immediately verifies `lo_stream.py` using the same
managed-file primitive as the other LOOK modules. `install.sh` also checks its
bytes at the final deployment boundary. An isolated import test checks that the
module works outside the development checkout.

## Verification

- Uploaded baseline: **735 passed**, after restoring executable modes stored in
  the ZIP. Python's extraction had dropped those modes; no source fix was needed.
- Updated suite: **755 passed — VERIFY OK**.
- Twenty new behavioral test cases cover fragment assembly, empty responses,
  tool-only responses, completion metadata, progress cadence, callback ordering,
  error/cancellation propagation, isolated import, and the real conversation loop
  with mocked Fabric and Ollama streams.
- Conversation-loop tests cover successful, failed, and cancelled turns on both
  transports, plus two-round tool continuations and accumulated usage metrics.
- No tests were removed or skipped.

Structural measurements for `ollama_chat()`:

| Metric | Before | After |
| --- | ---: | ---: |
| Lines | 1,515 | 1,495 |
| Structural branch complexity | 501 | 483 |

The small line reduction is intentional. The useful result is an independently
testable protocol boundary, rather than moving the entire conversation loop.

## Remaining audit priorities

1. Follow the final response through receipt enforcement, recent-exchange saving,
   and background memory extraction. Rendering uses `final`, while those save
   paths currently use `answer`; inspect cases where a later truth gate changes
   the message before extracting more policy.
2. Extract session-context assembly once the stable system-message slots and
   refreshed authority/resource context have independent behavior coverage.
3. Extract Unified Node command dispatch by command family, retaining its CLI
   arguments, JSON contract, and exit codes.
4. Separate pager key interpretation from rendering while preserving Browse ↔
   Filter navigation and terminal preview behavior.

No live three-machine installation or real model streaming was performed in this
workspace. The regression suite uses provider fixtures for the stream boundary.

## Applying the supplied patch

The bundle contains the complete updated source plus `lo-stream-audit.patch`.
To update the canonical Git checkout, run the following from its repository root,
using the actual path where you extracted the patch:

```bash
git apply --check /path/to/lo-stream-audit.patch
git apply /path/to/lo-stream-audit.patch
git diff --check
FC_PYTHON="$PWD/.venv/bin/python" bash tools/verify.sh
```

Inspect the diff, then use the existing commit/push and three-machine
pull/install workflow. This bundle has not been committed, pushed, or tagged.
