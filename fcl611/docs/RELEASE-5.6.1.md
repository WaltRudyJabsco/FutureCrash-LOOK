# 5.6.1 — File Catalog Concurrency Repair

- SQLite connections wait up to 30 seconds for transient writer contention.
- `PRAGMA user_version` is now written only during schema migration, not every connection.
- File scans use a portable Unix advisory lock so only one crawler writes a catalog at once.
- A second `lk scan` reports the active scan instead of crashing; catalog searches remain available under WAL.
- Fixes the macOS startup/background-scan race exposed immediately after 5.6.0 installation.
