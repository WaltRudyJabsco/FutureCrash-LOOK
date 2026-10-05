# LOOK Profile

## Status

`lk profile`

Shows schema, live roots, portable file count, configured backup root, retention, and inclusion/exclusion policy.

## Backup

`lk profile backup DEST`

Stores the backup root and creates:

```text
DEST/
  LOOK-profile-backups/
    YYYY-MM-DD-HHMMSS/
      manifest.json
      profile/
```

Subsequent `lk profile backup` calls reuse the stored destination. `--keep N` controls retained snapshots.

## Export

`lk profile export [FILE.zip]`

Creates one migration archive with `manifest.json` and curated portable state.

## Restore

`lk profile restore SOURCE`

SOURCE may be an export ZIP or timestamped backup directory. Restore validates schema and archive paths. Before overwriting live profile files, LOOK writes a local safety snapshot under:

`~/.local/share/look/restore_snapshots/`

## Secrets

Secrets are deliberately not included. Restore web/search keys and other secrets separately on the destination machine.
