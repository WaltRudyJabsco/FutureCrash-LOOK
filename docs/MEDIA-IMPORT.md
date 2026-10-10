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
lk media import watch FULL_JOB_ID --node 3090
lk media import cancel FULL_JOB_ID --node 3090
```

The workbench has N import, D rediscover, arrows select a job, Enter progress,
C cancel, and Escape return. Jobs continue when a window closes. Receipts show
stage, elapsed time, progress when the adapter supplies it, and estimated time
remaining when a meaningful percentage is available. Returning from a progress
view keeps the job running; cancellation terminates its own tool process group.

## Audio CDs

Linux uses cd-paranoia/cdparanoia for verified extraction, then ffmpeg encodes
lossless FLAC with title, artist, album and track tags. macOS can also encode the
mounted audio-CD AIFF files directly. MusicBrainz lookup uses the CD table of
contents when a reader provides it. One matching release may be used directly;
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
video. `--destination PATH` always refers to the owner's filesystem. Each job
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
