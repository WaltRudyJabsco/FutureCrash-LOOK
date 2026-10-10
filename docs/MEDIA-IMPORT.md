# Fabric disc import

The optical drive's node reads and encodes the disc. Other paired nodes submit
requests and watch job receipts. Verified files join that owner's existing media
catalog and can be played on another endpoint with the normal player/queue.

```sh
lk media import --node 3090
lk media import drives --node 3090
lk media import scan --kind cd --node 3090
lk media import start --kind cd --title "My Album" --node 3090
lk media import jobs --node 3090
lk media import watch --node 3090
lk media import cancel FULL_JOB_ID --node 3090
```

The workbench has N import, D rediscover, arrows select a job, Enter progress,
L deliver/retry, C cancel, and Escape return. Jobs continue when a window closes. Receipts show
stage, elapsed time, progress when the adapter supplies it, and estimated time
remaining when a meaningful percentage is available. Returning from a progress
view keeps the job running; cancellation terminates its own tool process group.

## Audio CDs

Linux uses cd-paranoia/cdparanoia for verified extraction, then ffmpeg encodes
lossless FLAC with title, artist, album and track tags. macOS can also encode the
mounted audio-CD AIFF files directly.

On a Mac, local requests run from the foreground terminal so removable-volume
permission applies to the actual reader; remote requests still use the owner's
node service and require that service to have volume access. Finder track numbers
are preserved in numeric order. macOS's `drutil` SupportLevel describes its own
drive support; it does not decide whether mounted audio tracks can be imported.

MusicBrainz lookup uses the CD table of
contents from cd-paranoia or the mounted macOS .TOC.plist. Finder names are
kept as fallback track titles. A single matching release preloads artist, album
and tracks; Return keeps those defaults. Without a match, artist is optional. One matching release may be used directly;
multiple releases are displayed for review rather than guessed. Choose a release
with the workbench or `--release NUMBER`; supply your own title to override it.
`--no-metadata` captures with your own labels offline. Unknown tracks keep
generic names; they are never silently assigned uncertain album metadata.

## DVD and Blu-ray

```sh
lk media import scan --kind dvd --node 3090
lk media import start --kind dvd --title "My Movie" --title-index 0 --node 3090
```

Use the index actually returned by scan: MakeMKV and HandBrake use their own
numbering. MakeMKV preserves the chosen title as MKV; `--title-index all` imports
all its titles. Without MakeMKV, HandBrakeCLI scans and encodes a chosen readable
source to H.264/AAC MP4. A title choice is required; the importer never guesses
which title is the feature. HandBrake does not remove copy protection. MakeMKV
availability, its own setup/license requirements and drive compatibility are
reported by its native output rather than hidden.

A Blu-ray-capable drive is required for Blu-rays. Apple USB SuperDrive is a
CD/DVD drive. Linux discovery checks optical block devices; macOS uses drutil
and diskutil; MakeMKV adds its native drive inventory. If a drive is missing,
check its USB connection and device access. SuperDrive behavior on Linux must
be verified with the actual connected hardware; no firmware is altered.

## Storage and recovery

Defaults: `~/Music/Fabric Imports` for CDs and `~/Movies/Fabric Imports` for
video. `--destination PATH` selects an owner-local folder. `--destination @node:ROOT`
selects a destination node’s canonical library root and uses background inbox delivery.
Without that override, the initiating node’s remembered `lk media storage` preference
chooses the destination. Each job
uses a hidden staging directory beside its destination, then validates media
streams/duration and publishes the directory atomically. Existing files are
never overwritten. A unique suffix distinguishes repeated imports. The final
directory contains descriptive sidecars and an import provenance receipt.
The media catalog and managed discovery roots are updated after publication.

Failed/cancelled jobs retain their partial directory and log; these paths are
shown in the receipt. Partial imports do not enter the media catalog. A scan or
codec failure never deletes the original disc/files. At least 1 GiB free space
is required to start; actual disc requirements can be substantially larger and
space exhaustion is recorded as a failed job. Job receipts and logs live under
`~/.local/share/look/imports/jobs/` on the owner.

## Setup

The unified installer offers optical and native notification helpers. It uses
Homebrew HandBrake on macOS/Linux and distribution packages
for Linux CD extraction, desktop notification and sound. Optional package
failures preserve the rest of the installation; `drives` reports available tools.
MakeMKV is detected when installed. Homebrew currently disables its macOS cask
for Gatekeeper compatibility, so automatic installation is unavailable. Use the
vendor’s normal supported setup; LOOK does not disable Gatekeeper.
Linux MakeMKV is detected when installed; follow its official setup rather than
adding an unreviewed repository or downloading a guessed build. `--no-optional`
skips these helper installations.

Sources: [CDDA Paranoia](https://xiph.org/paranoia/manual.html),
[MakeMKV CLI](https://www.makemkv.com/developers/usage.txt),
[HandBrake sources](https://handbrake.fr/docs/en/latest/workflow/open-video-source.html),
[MusicBrainz disc IDs](https://musicbrainz.org/doc/Disc_ID_Calculation).

Hardware status: the SuperDrive is not connected yet. Controlled import tests
verify orchestration and real FLAC encoding; real CD/DVD/Blu-ray acquisition
requires a compatible drive and disc for the final hardware check.

## Node libraries and inboxes

`lk media storage` shows the remembered library node and its mapped root.
`lk media storage --node 3090 --root "/run/media/jreno/2TB Storage/srv/media"`
maps an existing library and remembers it for future imports on this initiating
computer. Generic defaults use ~/Media; root/music, root/movies, root/tv,
root/books and root/inbox have stable meanings on every node. Existing files and
extra manually added scan roots remain independent.

A CD goes to music; DVD/Blu-ray goes to movies. Remote deliveries copy all audio,
sidecars and provenance into a hidden job folder inside the recipient’s inbox.
SHA-256 checksums are verified before promotion and cataloging. Delivery runs as
a detached job with a durable receipt; status/watch show it and cancel can stop
its owned worker. The ripping node’s original copy is always retained. Offline,
corrupt, interrupted or colliding deliveries report failure and retain source
copies; retries are explicit and checksum-matching destinations are reused.

Choose another library per import with --destination @node:ROOT, or use an
owner-local absolute/~/ folder to keep that import local. The workbench displays
the current default in its destination prompt; Return accepts it. Preferences
live in ~/.config/look/media_storage.json on the initiating node; each recipient
maps its own root in ~/.config/look/media_library.json.

To deliver an older completed import without rereading its disc:
`lk media import deliver FULL_JOB_ID --destination @3090:ROOT`.
Background delivery is separate from successful local encoding; its failure
never changes the local import into missing or deleted media.

## Deliver and watch without job IDs

On the computer that imported the disc:

```bash
lk media import deliver
lk media import watch
```

`deliver` uses the remembered library destination. A single undelivered completed
import starts immediately; several offer an album picker. You can also use
`lk media import deliver Grappelli` or an album title (multiple words are accepted).
Ambiguous names require a choice. `latest` and short job IDs remain available.
Successful deliveries are omitted from the default picker; naming one explicitly
allows delivery again to another destination. Existing destination files are
verified and never overwritten with conflicting content.

`watch` follows all active imports and deliveries on the selected owner. With no
active work, it shows the latest result. Add an album name to follow one import.
In a non-interactive shell it prints a snapshot; `--json` includes machine-readable
job IDs. `--node` selects another import owner.

In the disc workbench, select an album and press **L** to deliver or retry using the
saved destination; **Enter** shows progress. Failed transfers retain the original
album and an error receipt. Retry with **L** or `deliver ALBUM` when the recipient is
available. New imports already deliver automatically when a remote library is saved.
