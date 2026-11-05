# Fabric update

`lk fabric update` checks trusted nodes, the installed runtime, GitHub main,
and essential backup receipts, then shows a plan. It does not start work.

- `lk fabric update run --yes`: check and run the current plan.
- `lk fabric update run NODE --yes`: use that trusted node's installed release.
- `lk fabric update status`: inspect the persistent receipt.
- Add `--json` for structured output.

The existing `lk fabric update SOURCE TARGET... --yes` syntax still works.

In Signal or Albert, `/fabric update` opens the Observatory's update panel.
**Check Fabric update** prepares a one-hour review token; **Run reviewed plan**
starts exactly that plan after confirmation. A typed source chooses a trusted
node. Leaving it blank uses an installed copy of GitHub main when available,
otherwise prepares that exact GitHub commit. If GitHub is unavailable and bundles
agree, the installed runtime is used; divergent offline releases require an
explicit source. A GitHub check failure remains visible in the plan.

LO's explicit “update our fabric” request starts the same workflow. Descriptive
or negative requests do not authorize updates. Existing care/status commands remain.

## What runs

A detached worker serializes upkeep on each node and writes a receipt after each
step. It updates other nodes before the coordinator, waits for updater health
receipts, and uses existing rollback support. Runtime ZIPs are bounded, allowlisted,
syntax/checksum validated, and retain executable modes. This updates registered
LOOK runtime files, not operating systems, firmware, packages, or other repositories.
New dependencies or installer migrations still require their own setup.

Each node then runs Notes revision synchronization and enabled Mercury manuscript
synchronization, scans its Books folder, refreshes the Fabric Books and selected
Museum catalog caches, and checks media catalog availability. Ownership and
explicit offline copies are preserved; this does not mirror all media bytes.
Conflicts and unreachable owners are reported instead of being overwritten.

Configured essential-state backups and existing `fcl-books-backup` /
`fcl-museum-backup` integrations are checked and run when due. Recent restore-tested
receipts can satisfy the check. Missing backup configuration is **needs_setup**;
missing drives, failed jobs, or stale receipts are not reported as verified.
No drive is initialized and no new backup destination is chosen automatically.

## Receipts and retry

The Observatory polls the receipt; it does not hold a long-running browser request
open. `~/.local/share/future-crash-look/upkeep/` stores the current and archived
receipts. A complete job means its steps verified or were intentionally disabled;
failed, pending, or unconfigured steps produce a partial result. Offline nodes
remain explicit failures with a retry instruction. Run again when they reconnect;
matching runtimes are skipped. There is no silent indefinite retry or new schedule.

Browser mutations require endpoint authorization, JSON, same-origin requests,
and a recent locally generated review token. Only the local control plane can
coordinate a Fabric-wide update; trusted peers can request bounded local upkeep.
