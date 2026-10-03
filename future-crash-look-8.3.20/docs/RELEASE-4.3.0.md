# Future Crash + LOOK 4.3.0 — Fabric Packets

4.3 freezes the first durable work protocol underneath the Fabric.

- Adds immutable Fabric Work Packet `fwp/1`.
- Adds SQLite-backed durable jobs, attempts, results, idempotency, and append-only events.
- Adds local dependency gating for packet DAGs.
- Adds packet requirements, acceptance contracts, budgets, delivery target, provenance,
  authority grants and confirmation fields.
- Adds content-addressed SHA-256 artifact storage for referenced context.
- Adds remote packet forwarding to an advertised Tailscale node.
- Adds `lk fabric jobs`, `job`, `events`, `submit`, `packet`, and `cancel`.
- Fabric watch now consumes real event tapes from all advertising nodes, including Signal's
  existing supervisor lease events.
- Existing service mutation remains capability-scoped; packets do not expose remote shell.
- Fixes stale installer version constants in `install-look.sh` and installs/verifies the new
  packet core as part of the unified release.

The design rule is simple: prompts are execution details; Fabric carries work contracts.
