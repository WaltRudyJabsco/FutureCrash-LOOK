# Fabric Recovery 0.1

Recovery preserves the personal state that makes this Fabric yours. It is
separate from `lk profile backup`, which remains a portable, secret-free profile.
Albert's People/Places/Things interface is a later milestone; continuity comes
first.

## Commands

```sh
lk fabric backup inventory                  # local paths, sizes and exclusions
lk fabric backup status                     # destination and verified receipts
lk fabric backup init --uuid D050-B176       # once, on 3090 with FabBack connected
lk fabric backup run                        # encrypted backup + actual restore test
lk fabric backup run --due                  # at most once per day, if connected
lk fabric backup send jreno@3090.tailb77b68.ts.net
lk fabric backup collect jreno@m4-air.tailb77b68.ts.net jreno@3090.tailb77b68.ts.net
lk fabric backup restore /tmp/recovered-fabric
lk fabric backup restore /tmp/recovered-mac --host ORIGINAL_HOSTNAME
```

`fcl-recovery` provides the same commands. `lk settings` has a Recovery backup
row that opens the local status. `export NEW_DIRECTORY` and `verify DIRECTORY`
work without Restic on macOS/Linux. Exports contain plaintext secrets and are
mode 700 directories with mode 600 files; normally the exporter uses temporary
staging removed after encrypted storage. Keep manual exports protected.

## First destination: FabBack

The authorized filesystem UUID is `D050-B176`, currently mounted on 3090 at
`/run/media/jreno/FabBack` (exFAT). Its mount path can change. The backup system
uses the UUID and verifies a real writable mount before any write. It manages
only `FabricRecovery/repository` and its own authorization marker, refuses to
adopt an existing directory or follow destination symlinks, and skips an absent
drive. It never formats, partitions, mounts or deletes ordinary drive files.

Install Restic separately (`sudo apt install restic` on Ubuntu). Initialization
creates a random recovery password in
`~/.config/future-crash-look/recovery/key` on the repository owner, mode 600.
The key is never placed on FabBack or inside the backed-up capsule. Keep a
separate protected copy, ideally in a password manager/offline location.
**Without this key, the encrypted backups cannot be recovered.**

An SSH `send` exports this computer's state and streams it to the repository
owner's `fcl-recovery receive`. SSH must already trust the destination host key
and have authorized key access. Credentials do not pass through Fabric's HTTP
API, stdout, or logs. macOS can unlock its SSH key through the configured
Keychain. The receiver checks archive paths, types, duplicates, sizes and every
manifest checksum before backup, then checks the full Restic repository and
restores that owner's latest snapshot into a temporary directory. Successful
receipts are per source host. A source machine is protected only after its own
verified receipt exists; replicated notes are not a substitute for backing up
that machine's identity and local state.

## What is protected

- Fabric identity private/public keys, peer trust, service credentials and
  configuration, including Tailcat TLS keys.
- Fabric SQLite state, through the SQLite online backup API (includes committed
  WAL transactions without copying the live WAL).
- Notebook Markdown, immutable revisions and reminder delivery state, under the
  existing notebook lock.
- Fabric/LO memory, personality files, preferences, conversation history, saved
  Albert threads, artifacts, pending memory/skill queues, receipts and jobs.
- Media location catalogs and visibility preferences; release identifiers and
  installed-release manifests to guide reinstalling code.
- Existing Future Crash preferences, memory and task state.

The manifest records exact included paths, hashes, sizes, skipped paths and
exclusions. Consistency is per database/store: this is not a transaction across
all services. External editors can change Markdown independently; ordinary files
are checked for changes during copy and fail after repeated changes.

Excluded: referenced music/videos/documents, installed code, downloadable model
weights, generated file indexes, logs/caches/sockets/locks/PIDs, OS accounts/SSH
keys, other apps and their data. Symlinked sources are reported and skipped.
This is essential-state recovery, not a complete computer or media backup.

## Daily checks and recovery

The supplied systemd user service/timer checks hourly and writes at most one
verified backup per day when the drive is connected. Enable it only on a
configured repository owner:

```sh
install -m 644 core/future-crash-look-recovery.{service,timer} ~/.config/systemd/user/
systemctl --user daemon-reload
systemctl --user enable --now future-crash-look-recovery.timer
```

A Mac can call `fcl-recovery send --due USER@HOST` from launchd.
`collect SOURCE DESTINATION --due` streams a remote source through SSH to the
backup owner, so the M4 needs no copy of the repository password. The supplied
Mac launchd templates use the current three-node setup; replace `__HOME__` and
review their source/destination hosts before explicitly loading them. The M4
collection runs on the M3; it requires the M3 and both remote machines to be
awake/reachable, and retries at the next hourly check after a missed run. The normal
installer installs the CLI but does not authorize drives or enable schedules.
Backups retain all snapshots in this first version; no automated forget/prune
or deletion. A failed backup/check/restore never replaces the last verified
receipt. Disconnecting the drive is an ordinary skip, not permission to write
into its former mount point. Concurrent owner operations serialize through a
local lock.

Restores require a new directory and preserve the capsule's `home/` layout.
They check checksums and SQLite integrity and **do not activate identities,
overwrite live state, start services or merge into a living Fabric**. Check
`manifest.json` and install the recorded release before disaster recovery.
Only recover a node identity when its original node is gone; starting a clone
while the original is active would duplicate its identity. Reconciliation into
surviving nodes and full application startup on a blank machine are not yet
implemented/tested. The current restore test proves data recovery into an
isolated directory, not complete OS recovery.

An independent offsite repository and selected-document/media protection remain
follow-ups. FabBack alone is not protection against losing the drive itself.
