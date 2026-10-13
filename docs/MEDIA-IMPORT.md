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

`lk media import watch` and `lk media import jobs` read receipts across trusted
Fabric nodes by default. Active imports and deliveries appear with their owning
computer's name; unreachable nodes are listed separately. The interactive Fabric
monitor stays open while idle and refreshes as nodes reconnect. With no active
work it shows the most recent available result. Use `--node local` or
`--node NAME` to focus on one computer. A specific job selector still uses its
chosen node; cancellation and starting imports always remain owner-scoped.

Interactive progress views wrap long titles, stages, paths and errors to the
terminal's current width. Every continuation retains its import row's ink;
alternating shading advances for the next job, not the next screen line. Arrows
scroll when wrapped receipts fill the screen; Shift-Up/Down and Page-Up/Down move
by a page. Escape returns while the import continues. Piped text and JSON remain
unchanged.

The workbench has n import, d rediscover, h history, arrows select a job, Enter progress,
l send to library/retry delivery, c cancel, and Escape return. Uppercase variants
also work; Shift is not required. The inserted disc appears above a separate job
history section, with distinct label, title and status colors following the terminal palette.
The selected job uses the terminal theme's selection background across the row:
Paper uses its yellow highlighter, while Neon/Slate use their subdued selections.
The caret, subject, status and supporting ink retain readable contrast; surrounding
rows keep their normal background and alternating subject colors.
Jobs continue when a window closes. Receipts show
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

When CD fingerprint lookup finds no release, you can type the printed UPC/EAN
barcode digits. MusicBrainz searches that edition; confirm the release and disc.
Only media with the scanned track count are offered. A barcode is optional and
cannot guarantee a database match.

## TV box sets

Choose **tv** for the library category. First, optionally enter a Discogs release
or master link, `r12345`, `m12345`, or a numeric ID. A master offers specific
editions by country/year; confirm your physical edition. Then choose a disc when
the release supplies numbered positions. Public ID lookups need no account token;
automated Discogs name/barcode search is not implemented and requires authentication.
`0` skips the remembered edition suggestion. A confirmed edition is suggested for
later imports with the same series label, and is shown for confirmation again.

Discogs supplies release contents and extras. TVmaze supplements series/episode
numbers through exact title matches. Edition/disc suffixes are removed from the
suggested series search, without changing your import label. Headings and disc
positions never determine season numbers. Unique duration matches within two
seconds suggest a selection for review; duplicate or missing durations do not.
Unclassified release entries keep that status, instead of being called extras.
TVmaze also offers episodes in airing order and known specials. Confirm the series; choose an
episode number for each scanned disc title, `x Interview` (or another label) for
an extra, or `0` to leave it unidentified. Exact episode names suggest a choice;
generic names and durations alone never establish identity. Review shows the
mappings before starting, and `m` edits them. `all` keeps unmatched titles too.

Confirmed mappings use MakeMKV's scanned output filenames, not sorted file order.
Matched files receive readable series/season/episode names, descriptive sidecars
and catalog fields; extras remain explicitly labelled extras. Specials without an
episode number keep that distinction rather than receiving invented numbering.
Disc-only content absent from the provider needs a manual label. DVD menu recognition and DVD/Blu-ray barcode search are not implemented. Camera/case
recognition is not implemented. Metadata attribution: [TVmaze API and licensing](https://www.tvmaze.com/api), [Discogs API](https://www.discogs.com/developers).

## DVD and Blu-ray

The workbench selects a sole drive automatically and recognizes mounted CD,
DVD and Blu-ray layouts. If a layout is unavailable it asks for the disc kind.
The longest video title is offered as a suggestion; review its duration and
press Return to select it, or type another index or `all` explicitly.
Blank Return does not mean all titles.

Movie names are prefilled from Blu-ray metadata or the disc label. Labels are
only hints, not authoritative identities. The optional Wikidata lookup sends
the entered movie name and offers title/year matches for confirmation. No
match or a network failure keeps the entered name; selected metadata and its
source are preserved in the import receipt and video sidecar. CDs retain their
MusicBrainz album/track lookup. See [Wikidata data access](https://www.wikidata.org/wiki/Wikidata:Data_access).

Existing owner library configuration supplies the default destination when no
separate import preference exists. A changed category destination can be saved
for future imports. The final summary shows the title, kind and destination
before you start. H toggles completed/failed history without deleting receipts
or media; C cancels active work. L sends a completed import to the configured
remote library, including retrying a failed delivery.

Disc title scans allow up to five minutes; the Fabric request allows additional
transport time. A failed scan does not automatically rescan: choose `r` to retry,
`b` to go back, or `c`/Escape to cancel. No import starts until the final review.
The authenticated Fabric gateway also permits the full scan deadline; other
control requests retain their shorter limits. Gateway timeouts report an error
instead of silently dropping the connection.

MakeMKV's preparation and saving phases have separate labels and percentages.
A percentage reset at the start of saving does not mean copying restarted.
When MakeMKV is missing, the workbench links its official setup before offering
HandBrake for an unprotected disc. Install on the drive owner, then D refreshes
tool and drive discovery.

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

## Re-importing a different edition

To change from full-frame to widescreen, insert the desired side/disc, press `d`
to refresh discovery, then `n` for a new import. Review the scan and select the
desired title; duration alone does not establish its aspect ratio. Label it, for
example, `My Movie (widescreen)` so both editions are easy to distinguish during
review. The new import is verified and published in its own directory; the old
copy is never overwritten. There is currently no automatic replacement action.

Play the new copy and check its framing before removing the old full-frame copy
with LOOK's normal file browser. On the owning computer, rescan the same indexed
folder if it still exists: `lk media scan "/path/to/old-import"`. If you removed
the whole import directory, use `lk media scan --forget "/path/to/old-import"`
to forget that specific catalog root. This command changes the index only and
does not remove files. Refresh Media Find on other nodes afterward. Old job
receipts are history, not another playable copy; `h` hides completed history.

Other feature cuts and extras can be imported separately with descriptive
labels. A commentary may be an additional audio track inside the same title,
rather than a separate video title; MakeMKV's title/track selection determines
what is retained. LOOK does not yet offer a commentary-track selector.

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
MakeMKV is detected when installed, including executable user-local installs in
`~/.local/bin` when the background service's PATH omits that directory.
Homebrew currently disables its macOS cask
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

Artwork follows the selected physical copy. If a preferred drive is disconnected,
LOOK tries the other catalog locations for playback and cover previews. Duplicate
locations are copies of one logical track; they do not each need a downloaded cover.
Missing-cover lookup remains optional and uses the owner node's album cache.

### Choose the main library

Open `lk settings` and search for **Media library location**, or run
`lk media storage --pick`. Choose the home folder, an available mounted drive,
or a custom dedicated folder. The picker includes internal storage drives and
reuses an existing `srv/media`, `media`, or `Media` folder when available.
It shows the chosen node/path and asks before saving or creating the standard
`music`, `movies`, `tv`, `books`, and `inbox` folders.

Fresh installations use `~/Media`; no second drive is required. A server can
choose a separate internal drive to keep media off its startup disk. Backup
storage is configured separately. Changing the library location affects future
imports; it does **not** migrate existing files or remove their catalog entries.
Existing libraries can also be configured with
`lk media storage --node local --root /path/to/library`.

Raw DVD `VIDEO_TS/*.VOB` and Blu-ray `BDMV/STREAM/*.m2ts`/`*.mts` pieces
are excluded from the media library, including older cached disc scans. They
remain available to the import workbench and file browser. Finished imports and
standalone VOB/M2TS videos outside those disc structures remain cataloged.
