# Future Crash + LOOK 6.2.1 — Cheap Failure

Reliability patch for the Common Tongue intent substrate.

- `lk` imports `shlex` on every platform.
- Intent resolution has three cheap outcomes: resolved, clarify, no_match.
- Signal mounts browser video before requesting playback and ignores superseded AbortError promises.
- Browser media diagnostics distinguish source/network, decode, and unsupported-source failures.
- A source node is stopped only after endpoint-local browser playback actually starts.
