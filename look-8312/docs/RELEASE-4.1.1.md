# 4.1.1 — Fabric Truth

A reliability pass over Fabric Pulse.

- `fcl-node` inspection commands now query the resident node daemon instead of creating a fresh empty supervisor in the CLI process. `lk fabric activity` therefore shows real Signal/LO leases and completed history.
- The unified installer now treats the release as one atomic bundle: it verifies Fabric exists in both LOOK and the node source before mutation, stamps the installed release, byte-compares installed core files, and proves `lk fabric pulse` reaches the daemon before declaring success.
- LOOK release metadata is aligned with the unified 4.1.1 release; `fcl-node --version` is supported.
- Peer display prefers the Tailscale DNS label, avoiding duplicate generic `localhost` names.
- Generated-image auto-preview has a single owner. LO is told not to reopen the result, and a short same-process guard suppresses an immediate duplicate image launch.
- Signal version strings are reconciled at 0.6.1.
