# Future Crash + LOOK 4.2.0 — Fabric Control

The Fabric moves from discovery into controlled agency. Every live trusted node can now be inspected and asked to perform named, bounded capabilities from any other node, without becoming a remote shell.

## Added
- Remote node targeting for status, activity, pulse, models, qualification, and managed services.
- `lk fabric watch`: a live terminal-native monitor over Pulse + supervisor activity.
- `lk fabric models [NODE]`: compact capability/performance table; `--json` keeps raw diagnostics.
- Managed service vocabulary with explicit confirmation for mutations. No arbitrary command execution and no remote privilege escalation.
- `lk fabric services [NODE]` and `lk fabric service [NODE] SERVICE start|stop|restart`.
- Normal Fabric snapshot hides unrelated Tailscale phones/tablets; raw node diagnostics retain them.

## Fixed / refined
- Model qualification separates operational inference health from exact READY compliance; thinking-only output no longer becomes a false operational failure.
- Qualification requests disable thinking when supported and retain TTFT / token-rate evidence.
- Signal vocabulary is now compose → visual-model response → render; Comfy remains image generation.
- Signal visual-reflex prompt is smaller, thinking is disabled, and output is bounded to reduce the second inference pass.
- Signal supervisor telemetry now exposes visual-model waiting and final primitive rendering separately.
- 4.1.1 duplicate generated-image preview guard remains in place.

## Safety boundary
Fabric actions are capability-scoped. Observations are read-only. Mutating service actions require an explicit interactive confirmation (or `--yes` from a human-authored CLI invocation). The node never accepts arbitrary shell text and never elevates privileges remotely.
