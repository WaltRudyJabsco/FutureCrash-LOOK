# Mercury Writer companion

Mercury remains a separate application and repository. The unified installer
offers an optional pinned, SHA-256-verified Mercury runtime; it never copies
LOOK source into Mercury's repository.

```sh
./install.sh --mercury=install
./install.sh --mercury=off
./install.sh --mercury=install --mercury-source=/path/to/MercuryWriter
```

Interactive installs prompt once; unattended installs do not prompt or install
Mercury unless explicitly requested. The minimal companion has no Homebrew,
model-download or external Python package requirement. It verifies installed
runtime files, preserves existing manuscripts/settings, and adds `mercury` and
`mercury-server` to `~/.local/bin`. `mercury open` starts the local server on
demand; use an existing service manager for an always-running server.

## Ownership and routing

- Mercury owns manuscript IDs, revision ancestry, conflicts, writing context,
  its own AI memory and local offline replicas.
- The node advertises/probes Mercury on its default local port **8765**.
- Fabric owns discovery, bilateral trust, certificate-pinned transport and
  model placement. It does not expose Mercury's full HTTP API to peers.
- Guarded `/v1/mercury/status` and `/v1/mercury/exchange` relay only the bounded
  revision exchange to the local Mercury server. Authentication uses existing
  paired-node guards. `/v1/mercury/sync` dispatch is local-control only.
- A separate resident loop attempts enabled paired Mercury nodes every 15
  seconds. Offline/failing peers are reported without blocking note reminders.

Mercury model requests use the installed Fabric client when available. Mercury
retains its own prompts and memory; local/configured Ollama remains a fallback.
Research uses Fabric SearXNG before optional Ollama hosted search.

## Offline setup and validation

Install Mercury and this node update on each writing machine, pair the nodes,
then enable Project → Fabric copies or `mercury sync on` on each computer.
Run `mercury sync now`; inspect peer receipts and `mercury doctor airplane`
before disconnecting a writing machine. Both Mercury servers must be running.
Browser-only endpoints do not gain durable local replicas automatically.

Saves from all front ends share a per-project revision head. Exchange
fast-forwards only by ancestry; divergent drafts are preserved and exposed by
`mercury conflicts`. `mercury resolve PROJECT REVISION_ID` explicitly chooses
that draft and creates a revision acknowledging both branches. Keep independent
backups as well as replicas. Local deletion is not a Fabric-wide delete; local
exclusions prevent an old peer from immediately restoring a deleted project.
Mercury reset archives state and disables sync until deliberately re-enabled.

## Note links

`mercury link "My Novel"`, or Mercury's Copy project link button, creates:

```markdown
[My Novel](mercury:STABLE_PROJECT_ID)
```

LOOK Notes validates the ID and dispatches `mercury open ID` as an argv list.
Renames and directory moves do not affect links. Mercury opens the local
project or explains that a replica is needed; it never creates a manuscript
from a missing link. Links coexist with file, web, note and Wiki references.

## Boundaries

The current bridge uses Mercury's default local port. Custom standalone server
ports remain available through Mercury's `--port` and `MERCURY_URL`, but need
the default service for automatic node replication. Exchange batches fit the
existing 8 MiB ingress limit; individual revisions above 6 MiB need manual
export. Folder organization and availability preferences remain per endpoint.
The optional install and node update do not enable pairing or sync themselves.

## Managed companion updates

Paired nodes expose `POST /v1/mercury/install` with explicit `confirm: true`
and optional `enable_sync: true`. This operation installs only the pinned,
checksum-verified Mercury release; it does not accept commands, arbitrary
URLs or destination paths. `GET /v1/mercury/install/status` reports progress,
backups and verified running-version/offline-copy counts.

The helper retires only the known Mercury service or a process proven to belong
to its installed app. It keeps an app/state rollback copy, preserves configuration
and manuscripts, installs code, starts a user-managed local-only service, and
verifies its HTTP version before enabling requested sync. Failed upgrades retain
both the old app and failed app for recovery. This companion step follows the
ordinary LOOK runtime update; older nodes first receive the new guarded route
through their existing rollback-capable updater.
