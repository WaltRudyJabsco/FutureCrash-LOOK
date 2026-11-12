# Portable Fabric storage

`lk fabric storage` locates registered drives across paired, trusted nodes.
`lk fabric storage register` offers a drive chooser and prints a concrete plan.
Repeat with the displayed mount, name, role and `--yes` to commit registration.

Example travel library (folders must already exist):

```
lk fabric storage register --mount /Volumes/Travel --name Travel --role travel --path Books --path Music
# Review, then repeat with --yes.
lk fabric storage sync
lk fabric storage resolve Travel
lk fabric storage open Travel --folder 1
```

A **travel** drive exposes selected folders for local/offline browsing or through
its current trusted host. Registration does not copy media, change canonical
library locations, or import books/artwork into application catalogs.

A **backup** drive is identified as a recovery destination. Registration does not
initialize a repository, move encryption keys, change a schedule, or start a backup.
Use `lk fabric backup` on the configured backup owner for backup operations.
A backup repository is not a browsable copy of a travel library.

Each drive gets `.fabric-storage.json`; each account stores trusted registrations
under `~/.config/future-crash-look/storage/registry.json`. Only registration metadata
is synchronized, never recovery credentials. Nodes refresh about once a minute;
`sync` refreshes immediately. Disconnects and stale/unreachable hosts do not resolve
to old mount paths. Unknown drive markers require a matching trusted registration.
Previously synchronized nodes recognize drives offline. A fresh offline node must
first synchronize with a paired node before recognizing a registration.

Filesystem UUIDs are checked on the registration platform. The registered marker
provides identity across platforms whose filesystem UUID representations differ.
Cloned markers are not independent drives: simultaneous duplicate identities are
rejected. Register a separate travel drive separately; do not clone its marker.
This identity scheme is for trusted personal storage, not protection against a
malicious physical clone. The receiving OS must support the drive's filesystem.

LO, Signal and Albert share the read-only `fabric_storage` tool. It reports known
roles, current locations and selected folders; it cannot initialize or schedule
backups. API status is available at authenticated `/v1/storage`; peers exchange
local-only metadata at `/v1/storage/local`.
