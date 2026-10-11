# Archive TV and media handoff

Internet Archive playback uses LOOK's normal mpv queue. It streams published MP4
files directly, advances automatically, and repeats the queue. No videos are
silently downloaded or inserted into your personal catalog.

```sh
lk media archive                       # list channels
lk media archive play mtv              # early MTV; first four hours first
lk media archive play prelinger --shuffle
lk media archive play animation --limit 8
lk media archive item ARCHIVE_ID        # all available MP4s in one item
lk media archive find "music television"
lk media archive status                # readable status; --json for automation
lk meaty                               # the Mr. Meaty Easter egg
lk meaty --list                         # inspect episode order without playback
lk meaty --json                         # exact source files and URLs
lk meaty --extras                       # append shorts/promos after episodes
lk meaty --shuffle                      # explicitly shuffle instead
```

`lk player` provides existing space pause, left/right seek, p/n previous/next,
r repeat, x stop, and q/Esc close controls. Playback continues when the controller
closes. On an interactive terminal Archive playback opens that controller after
loading the queue. `lk media archive item` accepts an Archive details URL as well
as an ID. Availability belongs to Archive; private/restricted items are not
bypassed, and a channel reports skipped unavailable items. Channel requests are
bounded to at most 20 items; repeat cycles that queue rather than continuously
fetching the whole collection. An unavailable source can be skipped with Next.
Favorites and persistent per-program resume bookmarks are future work; existing
player transport and playlists remain available.

## Mr. Meaty order

Source: https://archive.org/details/mrmeatyallepisodesspecialspromosextra
Order reference: https://thetvdb.com/series/mr-meaty/allseasons/official

The paired-episode convention has 12 season-one files and six season-two files.
These play in numeric season/episode order, followed by **Big Greasy Musical**
and **Dream of the Dead** as specials. They are not arbitrarily assigned to a
third season. Shorts, training promos and compilations do not interrupt the
normal queue. The adapter chooses one MP4 per source file rather than playing
both an original and its `.ia.mp4` derivative. Missing expected episodes/specials
produce a clear error instead of calling a partial queue complete.

## Optional explicit download

```sh
lk media archive download mtv --directory ~/Videos/Archive
lk media scan ~/Videos/Archive
```

Download saves the first available MP4 of the specified item, prints its size,
requires sufficient space, checks the completed byte count, refuses overwrite,
and removes incomplete temporary files. It does not auto-import. For multi-video
items use `--json` to inspect the source inventory; selecting a specific file for
download is not yet provided. Streaming/downloading availability does not itself
establish a work's reuse rights; source attribution and item links are retained.

## Open with and Apple TV

In Media Find/Browse (and artist/album track selection):

- **O** uses LOOK's existing application chooser for the focused row.
- **T** on a Mac hands the focused local file to `/System/Applications/TV.app`.

The selector retains its filter/cursor after returning from the chooser.
These actions use one focused item, not an entire multi-selection. A physical
local copy may be used if the logical item has one; an identically named local
path must never impersonate a remote node's file. Remote-only files report that
you must copy or mount them first. There is no implicit multi-gigabyte download,
remote Apple launch, or promise that iOS accepts the same handoff.

A successful handoff means macOS accepted the open request. The TV app controls
import, codecs, account authorization and actual playback. Protected files still
require the appropriate authorized app.

Generic playback performs a bounded ISO-BMFF header check for encrypted sample
entries (`encv`, `enca`, `drmi`, `drms`) and recognizes `.m4p`. It skips media
payloads, does not infer encryption from `.m4v`, and does not decrypt anything.
Local player launch and owner-side Fabric media streaming reject recognized
protection before passing bytes to mpv. This is positive detection of known
markers, not a guarantee that every possible protected container is detected.
