# Conversational Fabric upkeep

Albert, Lo and Signal share two bounded tools: `fabric_status` and
`fabric_maintain`. They use the same trusted-node API and persistent receipts.
Clear requests run before model inference, so ordinary upkeep does not require a
large model or shell access. Less direct requests expose the same tools through
the shared cognition registry.

Try:

- “Check our Fabric.” — inspect installed releases, updater state and backups.
- “Are we all backed up and up to date?” — read-only check.
- “Make sure we're all backed up and up to date.” — check releases and run
  configured backup-owner plans if any node lacks recent verification.
- “Back up our Fabric.” — run existing backup-owner plans, including their
  configured contributors, even when previous receipts are recent.
- “Update all computers from this computer.” — synchronize trusted peers with
  this computer's registered installed release.
- “Update all computers from NODE.” — use the explicitly named trusted source.

Updates synchronize an existing installation; they do not fetch GitHub, install
packages or select the newest commit automatically. If releases differ, an
ensure request asks for a source rather than guessing which commit is newer.
The same release version can contain different commits. A matching digest means
installed bundles agree, not that they are the latest upstream release.

## Scope and evidence

Recovery covers Fabric identity, Notes and settings. Documents, photos and media
are excluded. A node counts as recently backed up only when its cryptographic
capsule-owner identity has a restore-tested receipt from the past 24 hours,
including receipts held by another backup owner. Invalid, future or stale dates
and unverified snapshots do not count. Unreachable nodes are reported as unknown.

No drive is initialized, new contributor added, recovery key exposed, or schedule
changed by these tools. Fresh installations report setup needed and point to
`lk fabric backup add` / `configure`. Existing configured plans and SSH transport
remain authoritative. Incomplete contributor collection is reported as incomplete.

Queued backups and staged updates are accepted work, not finished work. Ask
“check our Fabric” again to read job state and installed release digests. A backup
worker records completion only after restore testing. Disconnected drives, offline
nodes, old nodes without the new API, and failed workers remain visible failures.

Conservative Lo sessions are read-only. Workspace sessions, including Albert and
Signal, may use these narrowly scoped effects after an explicit human request;
arbitrary shell access is unnecessary. Tool arguments cannot widen the request
or invent an update source. Peer requests retain normal Fabric authentication;
Fabric-wide orchestration is only available on the owner's loopback control plane.

## CLI and API

```
lk fabric care status
lk fabric care ensure --yes
lk fabric care backup --yes
lk fabric care sync local --yes
lk fabric care sync NODE --yes
lk fabric care status --json
```

`fcl-node care` accepts the same arguments. Read-only status needs no `--yes`.
`GET /v1/care` inspects; `POST /v1/care` accepts `operation` and optional `source`.
Per-node `GET /v1/recovery/status` reports redacted status and receipts;
`POST /v1/recovery/run` starts an existing backup plan asynchronously. Jobs survive
service restart in the account's recovery state directory. These APIs never accept
arbitrary commands, destination paths, firmware operations or account credentials.
