# Set up Fabric backup

Connect and unlock an external drive in Finder or your Linux file manager. Then
open **Settings → Recovery backup**, or type:

```sh
lk fabric backup
lk fabric backup add
```

Nothing launches when a drive is plugged in. Opening backup shows whether this
account has a destination, its latest verified restore and the available actions.
The setup guide explains the scope, lists connected drives by name/capacity/free
space, asks where to save a spare recovery key, lets you choose other trusted
nodes and their accounts, and offers daily or manual backups. It shows a summary
before making changes, then performs the first backup and an actual restore test.

## What it protects

This is **essential Fabric state**, including identity, Notes/revisions, settings,
memories, durable state and Mercury manuscripts/revision history. It is not a
computer image or a backup of other documents, photos, music or video files. `lk fabric backup inventory` shows the exact local
inventory and exclusions. `lk profile backup` remains a separate portable,
secret-free profile.

The attached computer owns the encrypted Restic repository. Contributors keep
separate snapshots and do not receive its password. Every account configures its
own backup: setup never inherits another account's usernames, paired peers,
drive authorization or recovery key. Different accounts on one machine have
different snapshot owners, even if the hostname is identical.

## Guided setup

1. Install Restic if the guide says it is missing: `brew install restic` on a Mac,
   or `sudo apt install restic` on Ubuntu. Return to the guide afterwards.
2. Select a mounted, writable external volume. macOS uses Disk Utility's volume
   information; Linux uses its block-device inventory. Locked, unmounted,
   read-only and system volumes are not offered.
3. Choose a **new recovery-key file outside the selected backup drive**. The copy
   is private and never printed. Keep an independent copy in a safe place; losing
   the computer and its only key copy would also lose access to encrypted backups.
4. Include this computer and optionally select trusted Fabric peers. Enter the
   SSH account that owns each peer's state; the guide does not assume the same
   username. Remote Login/SSH and a verified key login must already work.
   An unavailable/unprepared account produces an actionable message before a new
   destination is initialized. Fabric pairing alone does not grant SSH access.
5. Choose daily or manual operation and accept the summary. The first backup and
   restore verification must succeed before setup enables its schedule.

The owner remembers the **filesystem UUID**, not its label or mount path. It
creates only `FabricRecovery/repository` and its authorization marker. Existing
files stay in place; existing recovery directories are never silently adopted.
There is no formatting, partitioning, automatic mounting or drive erasure.
One destination per OS account is supported in this version; Add shows an
existing configuration rather than replacing it.

## Everyday use

```sh
lk fabric backup                    # menu in a terminal, readable status otherwise
lk fabric backup status             # current destination and verified state
lk fabric backup drives             # connected external volume choices
lk fabric backup configure          # change contributors / schedule
lk fabric backup run                # back up all configured contributors now
lk fabric backup inventory          # inspect local scope
lk fabric backup key-copy NEW_FILE  # save another spare recovery key
lk fabric backup status --json      # structured status for tools
lk fabric backup drives --json
```

Daily means at most one verified snapshot per source per day, checked hourly
through a generated user-local launchd job on macOS or systemd timer on Linux.
The owner pulls selected accounts over SSH and verifies each capsule before
storage. Offline contributors do not stop other contributors; errors identify
the account and retry at a later check. Both the drive owner and the contributing
machine must be awake/reachable. A disconnected drive is a skip: the system never
writes into an empty folder at the former mount point.

Settings is also the place to discover what backup covers and how recovery works.
The installer installs the helper and points to Add; it never authorizes a drive,
imports another user's configuration or enables a backup schedule on its own.
Failed setup remains visibly incomplete and its background runner skips work
until configuration and verification succeed. The existing low-level `init`,
`send` and `collect` commands remain available for established setups. Previously
installed custom schedules are preserved by an upgrade; use Configure to adopt
this account's owner schedule, and review old contributor jobs before changing
how those sources are collected.

## Automation without the guide

All identifiers come from the user's environment. No example username, node or
volume is a product default:

```sh
lk fabric backup add --yes --mount '/Volumes/My Backup' \
  --key-copy "$HOME/Documents/Fabric-Recovery.key" --schedule daily
# Optional repeated --source USER@HOST adds explicit remote accounts.
```

`--yes` is explicit authorization of the supplied choices. Setup still validates
mount identity, spare-key location and contributor access, refuses overwrite,
and verifies a real restore. `--json` returns a structured setup result.
`fcl-recovery` exposes the same operations. The repository's older launchd
send/collect templates now contain placeholders only; guided setup generates the
active schedule without editing templates.

## Recovery and limits

```sh
lk fabric backup restore NEW_DIRECTORY
lk fabric backup restore NEW_DIRECTORY --host SNAPSHOT_OWNER
```

Find snapshot owners in the verified status receipts. Restores require a new
path, preserve the capsule's `home/` layout, and check checksums and SQLite
integrity. They do not overwrite live state, activate an identity, start services
or merge into a surviving Fabric. Local restore can still read snapshots from
before account-specific snapshot naming was introduced. Reconciliation and full
OS recovery remain future work.

Backups are encrypted; the owner key is stored privately in
`~/.config/future-crash-look/recovery/key` and excluded from recovery capsules.
Exports contain plaintext secrets: use the normal encrypted backup flow rather
than leaving exported directories around. There is no automatic snapshot pruning.
An independent offsite destination and selected-document/media protection are
future work; one attached drive alone is not protection against losing that drive.

Conversational checks and configured backup runs: [Fabric care](FABRIC-CARE.md).

## Mercury manuscripts on FabBack

Mercury writing data is an explicit exception to the general document exclusion.
The inventory includes only the known Mercury app's `library`, `state`, `history`
and `workspace` trees and its writing configuration/memory, on macOS and Linux.
It does not traverse arbitrary Documents folders or include Mercury runtime code.

Mercury's writer lock holds the manuscript/revision inventory consistent during
export. Verification checks every file checksum and each manuscript head against
its immutable revision body. Encrypted backup receipts include Mercury project,
revision, file and byte counts only after the Restic restore check succeeds.
Old essential-state receipts without Mercury coverage do not count as current
manuscript protection. Existing FabBack destination, keys, schedules and unrelated
drive contents are preserved. Replication brings writes to the 3090; its existing
backup plan protects the resulting point-in-time library and revision history.
