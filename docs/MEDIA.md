# Media

Media is a Fabric capability with endpoint-local presentation.

## Catalog, queue, playlist

The Fabric catalog answers *what media exists and on which node*. A queue answers *what this endpoint will play now*. A playlist is a saved queue. Keeping these separate prevents one endpoint's browsing or playback from unexpectedly changing another endpoint.

## Audio and video desks

`lk mp [QUERY]` opens the audio desk: music, podcasts, recordings, audiobooks and
other cataloged audio. `lk tv [QUERY]` opens the video desk: movies, TV episodes,
personal videos and cataloged online videos. `lk media mp` and `lk media tv` are
aliases. Existing downloads such as `lk ytd URL` appear after cataloging; TV does
not automatically browse or download online services.

Both desks share the existing endpoint player, queue, metadata editor and Fabric
source selection. Opening either desk never starts playback. The library and
queue lists show only that desk's media type; the transport shows the actual
shared player's state, even when another type is playing. Transport actions still
control that shared player. Starting marked items replaces its current queue;
adding items appends to it. This is one player, not two independent streams.

Aligned columns distinguish titles from artists/albums or series/episode details.
The palette retains alternating rows and a full selected-row highlight. The
header always shows sorting and image/ASCII mode; the selected item's source sits
below the list. Wide terminals show quiet artwork/video stills beside the list;
narrow terminals retain the list and selected details. Previews never autoplay.

In `lk tv`, **Shift-O** opens with a local application and **Shift-T** hands the
focused video to Apple TV on macOS. A remote source uses the existing explicit
temporary/keep copy review before handoff; no transfer starts from a preview.
Authorization/playback of protected purchases still belongs to Apple TV. Linux
reports the Mac requirement without attempting a transfer. These keys remain
actions while editing TV search, and apply to the focused item.

Use **Shift-F** to cycle sorting, **Shift-G** to reverse, **Shift-M** to toggle
image/ASCII, **Shift-L/Q** for library/queue, **Shift-E** for metadata, and **Tab**
to mark. Enter plays; **Shift-B** adds to the queue. `/` edits search; Escape
finishes search, then clears it, then exits. Lowercase transport shortcuts retain
space pause, p/n previous/next, arrows seek, s shuffle, r repeat, x stop and v
visuals. `lk media find` remains the broader catalog/visibility management view.

## LOOK Media Find

Media Find and LKMP use subtle alternating foreground tones, with distinct
artist, title, album and source inks. Selected rows use the terminal palette's
selection background, retain muted supporting details, and show alerts in amber.
LOOK's file lists share the same treatment while retaining file-type and Nerd
Font icon colors. Selection styling ends at each row or column cell; surrounding
backgrounds retain their usual transparency.

`lk media find QUERY` is both a catalog search and a lightweight playlist builder. Filtering follows LOOK's include/exclude grammar. `clash london` requires both terms; `clash \\live \\remix` requires `clash` while excluding rows containing `live` or `remix`.

Lowercase `q` is filter text, including in artist/album browsing. Escape exits; uppercase `Q` keeps its queue action.

Controls: Tab toggles the focused row; Shift-A selects/unselects every currently visible row; Enter or Shift-P plays selected rows (or the focused row); Shift-Q appends selected/focused rows to the queue; Shift-S saves selected/focused rows as a playlist; Shift-C clears selection; Shift-I shows identity/details; Esc clears the filter and then exits.

**Shift-F** cycles Default → Title → Newest modified → Recently added → Type →
Largest first. **Shift-G** reverses the current order, matching LOOK's sort/reverse
convention. The header shows the criterion and reversed state; these choices
combine with search, hidden/source modes and marked selections. Type groups audio
and video, then file format; reverse puts video before audio. Lowercase `g` and `f`
remain search text. Shift-Left/Right (or Home/End) jump to the list's beginning/end.

Recently added uses the entry's recorded catalog arrival, preserved on rescans
and background refreshes. Older entries with no recorded arrival stay last in
both directions; file modification time remains a separate order. These view
choices apply to the current browsing session. Photos are not part of Media Find's
audio/video catalog.

Shift-I also opens the existing quiet artwork/details preview. At widths of at
least 78 columns, a small terminal image appears beside the details when artwork
is available. The remote owner can extract a video's first frame and return only
the tiny terminal preview; navigating the list does not start playback. An opening
black frame, missing source or unavailable decoder can still yield a poor/missing
preview. This is a still-image preview, not automatic audio/video auditioning.

`/` starts search editing. Enter or Esc finishes editing while keeping the filter.
Arrows, Tab, and selection actions work directly on the filtered results, including
while editing. A subsequent Esc clears the filter; another exits.

In `lk mp`, Shift-A likewise selects/unselects all visible results and Shift-C clears
marks. Shift-B adds marked results (or the focused row) to the queue; Shift-Q shows
the queue. Enter plays marked results or the focused row after search editing ends.

## Catalog health and scan roots

Media Find shows **CATALOG OWNERS** with each node's physical location count.
The shown count is the filtered logical list, not a count of files on the current
computer. Offline owners retained from the last known catalog are labeled cached;
FABRIC PARTIAL lists unreachable owners and FABRIC STALE identifies a local-node
fallback. Partial snapshots are retried after three seconds rather than occupying
the normal 45-second cache window. R refreshes owner health as well as entries,
and removes locations that disappeared from the current snapshot.

LOOK decodes both compressed and ordinary catalog responses. If the local request
fails, the fallback or stale-catalog line includes its actual error; `lk media
fabric` also prints the diagnostic. Re-pairing is not required for a local decode
failure. Fabric doctor probes alternative routes independently: one failed route
does not make a peer unavailable when another authenticated route works. Tailcat's
pinned certificate applies only to its advertised HTTPS host and port; the
Tailscale HTTPS fallback keeps normal certificate and hostname verification.
Short-lived discovered IP routes survive advertisement refreshes while the
paired Tailcat certificate remains unchanged.

Large catalog requests try the peer's advertised DNS fallback before exhausting
the budget on another LAN address. A successful bulk-transfer route is remembered
for 90 seconds; ordinary control route order and authentication stay unchanged.
Passing a small health probe does not guarantee a large catalog transfer succeeds.

An explicit scan reconciles all indexed files inside its scope, including nested
import folders: deleted files disappear while surviving imports keep their own
root identity. Unrelated offline roots and unreadable subtrees are preserved.

Simultaneous catalog readers share a local publication for up to three seconds;
changes to the catalog or owner visibility file invalidate it immediately. Old
TypeScript-heavy broad scans use a bounded byte search for MPEG sync candidates
instead of checking every candidate offset in Python. This keeps publishing a
large library from repeating expensive work for each peer browsing it.

Large peer catalogs have an eight-second per-route read timeout and an eighteen-
second route budget; LOOK allows 45 seconds for the complete local-node response.
A sleeping peer must not make LOOK discard a healthy owner's catalog merely
because the earlier eight-second overall request expired.

`lk media library` lists indexed local roots. A scan of `/` includes application
sounds, sample packs, and system assets; those are real files but usually not your
music library. Overlapping scans now count a physical path once and prefer its
more specific scan root. TypeScript `.ts` source files are excluded; genuine MPEG
transport streams retain support based on packet sync bytes.

To remove an unwanted scan from the catalog:

```sh
lk media scan --forget /
```

This writes a dated catalog backup and forgets entries owned by that scan root.
It does not delete, move, or modify media files, and separately indexed Music or
other specific roots remain. Choose the root on its owning computer; this command
does not silently curate another node's library. Existing broad scans are not
automatically removed by installing an update.

Artwork browsing prefers embedded covers, image sidecars, and sibling-track art.
With online lookup enabled, when all are absent a background worker searches MusicBrainz by album artist and
album title, requires an exact normalized match with a unique release group and a
high search score, then downloads its Cover Art Archive 500-pixel front cover.
Ambiguous albums are skipped. Lookups are rate-limited, deduplicated by album,
and cached under ~/.cache/look/album-covers on the owner. The online fallback
never changes audio bytes, embedded tags, or user cover files. Only artist/album
metadata is sent to the public provider. The owner serves the downloaded image
and terminal preview through the existing Fabric artwork routes.

A first miss may remain visible until the background job finishes and the preview
retries (up to twenty seconds). Temporary provider failures retry after five
minutes; absent/ambiguous matches after six hours. JSON cache records include the
state, reason, provider URL and matched release-group ID.
Use `lk media artwork on` on each owning node to enable lookup, and `lk media artwork
off` to disable it. The default is off; `lk media artwork status` reports the setting.
The setting applies to LOOK and its node daemon and persists across runtime updates.
LOOK_MEDIA_ARTWORK_LOOKUP=1 or 0 overrides it for a process. Cached and existing
art remains available when disabled. Matched CD imports
continue to save their original cover sidecars.

Catalog responses now stream in chunks through Tailcat/ingress with a catalog
transfer timeout, rather than being buffered behind the ordinary control/header
deadlines. Updated nodes negotiate gzip JSON; older peers can still consume plain
JSON. This prevents a healthy large catalog from being truncated mid-transfer.

## Hidden media

In Media Find, Shift-X hides selected items, Shift-D chooses a directory to hide,
Shift-H shows hidden items, and Shift-U removes a visibility rule. New hide/unhide
changes are stored on each file's owning node and published with its catalog, so
other devices honor the same choice after refreshing their catalog (normally
within the 45-second cache window). A directory rule affects that owner's path;
it does not hide an unrelated matching path on another node. Hiding a logical
item applies to every known physical source. Bulk hides use one request per
owner. If an owner is unavailable, the status reports that the change did not sync.

Older endpoint-local exclusions remain local. Reapply Shift-X or Shift-D to make
those choices Fabric-wide. Shift-U clears both the local rule and the owning
node's corresponding rule. Each source node and browsing endpoint must run this
update. A view already open on another endpoint needs reopening to refresh.

For playback failures, select/play the affected item, then run `lk media doctor`
on the playback machine. It reports the actual source, decoder probe and recent
mpv log. A successful probe is evidence of decoding, not proof that rendering
or sound output works correctly. LKMP retains its latest launch receipt and shows
failed playback instead of reporting “playing” when the player launch fails.

For a silent player after headphones disconnect, press **Shift-O** in `lk mp`
or `lk player`, or run `lk media audio reset`. This reopens only LOOK’s mpv audio
output on the current system default, retaining the queue, position, pause state
and volume. It does not change OS output settings or Bluetooth pairing. A paused
Mac player also refreshes its automatic output when explicitly resumed. Existing
video-desk Shift-O continues to mean Open With.

`lk media audio` reports the player’s configured output, backend, mute, volume and
pause state without changing them. `auto` means follow the system default; it is
not a speaker’s name. An accepted reset is not proof that sound is audible.

## Albert

A Fabric media result may contain a complete queue. Albert retains that queue, displays the current position, advances automatically at track end, and provides previous/next/clear controls. A later audio play result replaces the earlier Albert audio queue.

Albert stores `{node,id}` for catalog items. At playback time it requests `/api/media/ticket`, assigns the returned same-origin `/api/media/audio` URL to the native media element, and lets the facade proxy Range requests to Fabric. The native `<audio>` element remains the playback engine; visualization is presentation-only.

## Artist and album browsing

`lk media artists` opens artists → albums → ordered tracks. `lk media albums`
opens albums directly. Enter opens the selected group; Escape returns to its
parent. Tracks retain Media Find playback, selection, queue and playlist actions.
Albums are grouped by album artist plus title, keeping identically named albums
separate while supporting compilation album-artist tags. Disc and track numbers
control order. `--list` retains a printed listing; `--json` returns group data.

## Optical import

`lk media import` opens a disc workbench. `--node 3090` selects a paired owner.
See [Disc import](MEDIA-IMPORT.md) for drive discovery, supported adapters,
metadata review, title selection and background-job progress.

## Correct artist, album and track information

In Media Find, album tracks or LKMP, mark tracks with Tab (A selects all shown),
then press Shift-E. Choose `s` for shared corrections or `i` to name each item
individually. Music fields include artist, album artist, album, disc, title and
track. Video fields include series, season, episode, title and content kind
(`episode`, `special`, `extra`, `unclassified`). Each field has a numbered heading
and a short explanation. Current values are filled into the editor: use arrows
and Backspace to change just part of a name, then Enter to accept. An unchanged
or blank field keeps its value; `-` clears a TV field. Esc cancels before saving.
When a shared field has different values, it starts blank; typing a value applies
it to every selected item, while blank keeps each item's own value.
Review all proposed changes before saving. Individual mode gives each selected
episode its own title and number, without leaving the editor between items.
Media Find and LKMP show TV series names in the artist position and season/episode
details in the album position. Keep the episode title in Title; the series name
is shown separately. Music metadata is unchanged. Type sorting groups TV by
series, season and episode number.
Corrections apply to every listed source of each item, including remote files.
Offline or read-only sources report failures; successful sources are counted
separately. Refresh before retrying a stale selection. Filenames stay unchanged.
The final review shows the changes before saving. R refreshes
the view after an import or a correction elsewhere.

For a whole album, open `lk media albums`, open the album, then A and E.
For an explicit command-line batch:

```sh
lk media edit "Just One of Those Things" --artist "Stéphane Grappelli" --all
lk media edit --help
```

Corrections live beside the media in .info.json and update the owning catalog.
They survive rescans and appear across the fabric; embedded audio/video tags
and media bytes remain unchanged. Keep each sidecar when moving files. Editing
an artist also updates album artist when it previously matched or was empty;
explicit compilation album artists remain intact. Each owner validates each submitted
batch before writing, checks for stale metadata, and restores sidecars if
saving fails. Multiple-owner edits report each failure and the successful count.

## Imported album artwork

Matched audio CDs download a 500-pixel front cover from the Cover Art Archive into `cover.jpg` beside the tracks. Existing artwork is preserved. Missing art or an unavailable service does not fail the import; the job records its artwork result. Covers travel with inbox delivery and the owning node serves them to remote media browsers.

## Player visuals

In `lk player`, press lowercase `v` to cycle Bars, Waves, Orbit, Tunnel, Stars,
Plasma, **Album Art**, **Black Hole**, **Rooftops**, **Spectrum**, **Moon Jelly**, **Firefly Garden**, then **Cycle**, followed by the
normal player view. In `lk mp`, `v` opens the same player visuals. Cycle rotates through the twelve
visualizers every ten seconds while its view is open, including Album Art, and
never switches automatically to the normal player view. Selecting Cycle starts
at Bars; pressing `v` again returns to the normal view. Transport controls remain
available throughout. Album Art fills the available canvas with a centered ASCII
cover while keeping track information and transport controls visible. Covers
preserve their proportions for terminal cells, and remote covers load in the
background. Missing artwork displays an availability message. While playing,
a narrow diagonal foreground highlight crosses Album Art for three seconds every
18 seconds, beginning five seconds after entering the view. Pausing disables the
highlight; each track keeps its existing foreground color. Black Hole draws a
rotating ASCII accretion disc around a dark horizon with a curved arc of light.
Rooftops is a miniature city run with three scrolling depths and a runner whose
jumps follow the rooftop gaps. Spectrum draws EQ-style columns with a warm-to-green
foreground gradient and fading sparks. Black Hole has a rare UFO flyby when left
open: a six-second pass beginning after 12 seconds, repeating every 47 seconds.
These animations are ambient, rather than measurements of the audio signal.
The Rooftops scene is also a playable [LOOK game](GAMES.md); its soundtrack is
exclusive to the game and never runs in the visualizer.

When a track has multiple catalog locations, playback checks local copies first,
then remote copies. Missing local paths fall through to reachable remote copies;
a remote timeout is used only after confirmed alternatives have been tried.
This chooses availability and locality, not bitrate or codec quality. Multiple
locations do not establish a verified backup. The configured library destination
is an import destination; Fabric Recovery essential-state backups exclude music
and video bytes.

## Browser video preparation

Signal and Albert show a preparation/loading message before browser video becomes
ready, and a source-error message if loading fails. Preparation is performed on
the file's owning node and cached; original rips remain unchanged. For H.264 video
with 8-bit 4:2:0 pixels, the owner first copies the video into MP4, copying compatible
AAC/MP3 audio or converting other audio to AAC. If that fails, or the video needs
conversion, the existing H.264/AAC encoder is used. Remuxing reduces preparation
work, not the original video's bitrate or storage requirement. The current browser
representation still finishes before serving; segmented/adaptive streaming is not
implemented by this update.

Browser movie representations use mono/stereo AAC or MP3 when already compatible;
other movie soundtracks are converted to stereo AAC at 48 kHz. This keeps the
browser copy conservative for phones/tablets while native playback and original
rips retain their original audio channels. Older browser cache copies rebuild
when the representation changes.

### Full-screen browser players

Signal and Albert have a **Full screen** button for video and audio. Video keeps
its native playback controls and fits the screen without cropping. Use **Exit
full screen**, Escape on a keyboard, or the device's native Done/back control to
return to the inline player. Playback position and the playing media element are
preserved. Albert's existing expand/contract option remains available separately.

Audio opens a larger view of the title and artwork/activity visualization, with
playback controls. Signal keeps its ASCII/Image/Art off choices and adds subtle
ambient bars; these are decorative activity visuals, not measured audio levels.
Albert enlarges its existing audio activity display. Neither changes audio routing.

The button requests the browser's full-screen mode directly from your tap. On
Apple browsers that only support native video full screen, it uses that video
player. Where system full screen is unavailable, the player fills the browser
viewport with the same exit button; browser chrome may remain visible.

Media Find shows readable type labels (Audio, Movie, TV, Video, Podcast), plus
aligned Artist, Title and Album columns when space permits. Narrow terminals
use a compact title-first row. Movie/TV/Podcast labels use explicit category or
folder context; unknown audio remains Audio. This does not add photo/PDF scanning.
Shift-F's Type order groups by album artist (falling back to artist), album, disc
and track number; different codec formats no longer split an album.

Shift-T hands a local file to Apple TV on a Mac. A source stored on another node
must first be copied or mounted on that Mac. The error names the source owner;
Shift-T does not transfer files or change Apple TV's playback authorization.

Video previews use a cached still at the earlier of one minute or 20% of the
clip's duration. Unknown-duration clips try one minute, then the opening frame
if that seek produces no image. Explicit poster/cover files take precedence.
Local and Fabric previews share this frame; the movie itself stays unchanged.

### Find, MP and the ASCII player

Media Find is the inspection/curation surface (types, sources, visibility and
metadata); MP is the approved-visible library, queues and playback workspace.
Existing shortcuts remain available. Media Find's Shift-I info pane and MP's
artwork pane automatically promote ASCII to native images in Kitty/iTerm when
supported. Shift-M toggles Auto/ASCII. Other terminals keep ASCII;
`LOOK_NATIVE_PREVIEW=off` disables native images. Remote images are fetched as
small cached cover/preview assets, not full movies or songs.

MP has a live now-playing panel beneath the list. Space toggles play/pause;
p/n skip, left/right seek, s shuffles, r repeats, and x stops. Progress updates
preserve the list and native artwork. Lowercase v opens the dedicated ASCII
player/visualizer, now including Clockwork Garden in its ten-second rotation.


### Preview and local Apple TV copies

Media Find: **Shift-I** opens the preview; **Shift-M** toggles Auto image/ASCII.
MP uses the same Shift-M toggle in its side pane (terminal width at least 96 columns).
Native images need Kitty or iTerm; other terminals retain ASCII. On macOS, preview
conversion explicitly produces PNG, including when the source cover is JPEG.
Invalid image preparation leaves the ASCII fallback visible.

MP library supports **Shift-F** sort cycling and **Shift-G** reverse, matching
Media Find. Queue order remains playback order; switch to **Shift-L** to sort the
library. Lowercase f/g/m remain filter text.

On a Mac, **Shift-T** uses an existing local file or offers to copy a trusted remote
source. Choose `t` for a temporary playback cache or `k` to keep it in this Mac's
configured library. The confirmation shows source size, destination and free space.
The original stays on its owner. Failed or cancelled transfers do not publish a
partial movie. Completed copies are checked for length and local checksum (and
source digest where available); permanent copies are scanned into the local catalog.
Temporary files remain in `~/.cache/look/playback` until explicitly removed; close
Apple TV before removing them. Apple TV still handles account authorization.
The transfer serves original bytes, without decrypting or transcoding protected media.

The Find header's indexed-location count includes hidden entries and backup copies.
The shown count is the current logical, visible result. Broad scan roots can therefore
produce a much larger indexed count without making those files playable library items.

Movie preview extraction and remote JPEG caches share a frame-version marker.
Updating the frame-selection rule refreshes old remote images even when movie
files are unchanged; album-cover caches retain their existing identities.


### Import setup and navigation

`lk media import` → `n new import` asks for disc format and library category.
CDs use Music; DVD/Blu-ray can use Movies or TV. The destination follows the
chosen category in your configured library. TV suggests `all` with MakeMKV;
review the scan because all titles can include extras as well as episodes.
Use the series/season/disc label to keep multi-disc sets distinct. Movie title/year
lookup remains optional; TV imports keep the label you supply.

Destination supports Tab completion (ambiguous completion can open the picker),
Right/Down for the existing LOOK folder picker, Ctrl-U to clear, and literal paths
with spaces or Unicode. Long paths scroll within the input line. Remote addresses
retain `@node:/library-root`; the selected category is added on the owner.

Escape goes back one setup step; Escape at the first step cancels the new import
and returns to the workbench. At review, `k` edits format, `c` category, `i` title
selection, `m` name/metadata, and `d` destination. `y` starts; `n` cancels. Existing
jobs continue while you edit. Library preferences are saved only after confirmed
submission when you explicitly choose to remember the destination.

CLI example: `lk media import start --drive /dev/sr0 --kind dvd --category tv
--title "Series Season 1 Disc 1" --title-index all` (enter as one command).

Music playback keeps mpv artwork windows disabled; LOOK owns terminal artwork.
Video still opens its viewer. Reusing a previously visible player for music clears
its forced-window setting before loading the audio queue.

Browser queue preparation uses one catalog snapshot per request. Remote
preparation/play deadlines outlast the node worker; pause/seek and other ordinary
control calls retain short deadlines. Signal reports preparation timeouts or
connection failures explicitly. Preparing a queue does not start native playback
and does not prove that a browser can decode the selected movie.


## Media desk navigation and landscape layout

In `lk mp` and `lk tv`, Shift-Q toggles Library/Queue. Escape from Queue returns
to the previous library filter, cursor and marks; Escape in Library clears its
filter before exiting. Shift-L also returns to Library. No quit confirmation is
needed for this reversible navigation.

Shift-W opens a sibling shell from MP, TV, Media Find or the import workbench, using the same
Kitty/tmux helper as LOOK, Notes and Web. Kitty's Option-Shift-W changes focus and
Ctrl-Shift-W closes the focused pane; the footer shows these controls after a
successful split. The terminal owns pane focus, borders and inactive-text dimming.
LK Player remains a playback endpoint without shell-pane creation. Shift-W in
a text editor remains typed text.

Narrow media desks retain their compact layout. Wider list areas add LENGTH and
expand artist/title/album columns across the available landscape width. Cached
catalog durations appear immediately; unknown lengths are probed one at a time
for visible rows only, using ffprobe and the existing local/Fabric source path.
No audio is played for this lookup. Results are cached by source identity, size
and modification time; failures remain `--:--`. Browsing never waits for a whole
library metadata scan. Lengths can therefore appear progressively.


### Album-title variations in cover lookup

The online cover fallback searches the original album title first. If there is
no match, it may retry without one trailing parenthetical/bracketed qualifier.
That retry requires the same artist, an exact base title, a 100% provider search
score and one unique release group. Ambiguous matches remain unresolved.
Live, acoustic, remix, demo, instrumental, tribute and part/volume qualifiers
remain distinct. Covers stay under the original album cache identity; file names,
audio bytes and tags are unchanged. Older negative title-match results are
retried after this matcher update. Provider failures retain their retry backoff.

## Standard audio delivery

Remote audio in LK Player, LKMP and LKTV uses the owning node's **Standard**
representation by default. FLAC, WAV, AIFF and ALAC become cached **192 kbps
AAC in M4A**. Existing compressed audio (including MP3, AAC and Ogg) passes
through directly in terminal players; M4A containers are checked for ALAC.
Local playback keeps the original. Video delivery is unchanged.

Signal and Albert share the same owner-side AAC cache. A cache miss encodes on
first request; subsequent playback and seeking use the complete cached file and
normal HTTP byte ranges. A changed source invalidates its cached rendition.
Only the cache is written: masters, tags, catalog IDs, queues and artwork stay
associated with the original song. Availability and duration previews use the
original path and never request an AAC conversion just to draw a list.

The first terminal request allows up to 90 seconds for source preparation and
still requires an actual decoded media clock before reporting playback. Ordinary
sources retain their existing startup deadline. To explicitly stream originals
from a terminal, launch with `LOOK_MEDIA_AUDIO_QUALITY=original lk mp` (also
works with `lk player`). This is a delivery choice, not a CD import setting.
CD imports remain lossless FLAC. Keep Offline continues to copy and verify the
original file; it does not silently substitute different bytes.

**Magnetic Field** and **Comet Trails** join the ambient visualizers and the
10-second Cycle rotation. They use the terminal palette's foreground inks and
remain still while paused.

## Responsive catalog filtering

MP, TV and Media Find prepare visibility and duplicate grouping once per catalog
view, instead of repeating the whole Fabric scan for every typed letter. Search
terms retain the existing include/exclude syntax, Unicode matching, physical-source
matching and queue order. Refresh, metadata edits and visibility changes rebuild
the prepared view; ordinary typing reuses it.

Artwork extraction and player-status IPC run outside the input thread. Only the
latest preview request is retained while one is running, so fast typing cannot
create a queue of obsolete cover jobs. Background status snapshots are read-only
and cannot overwrite queue changes. Layouts and key bindings stay the same.

While `/` search is active, every printable character—including capital shortcut
letters—is search text. Paste is literal text too; embedded newlines become
spaces. Arrows can move through results without ending text entry. Enter or
Escape returns to browsing, where the normal letter shortcuts remain available.
Unknown terminal replies and keyboard key-release packets are ignored rather
than interpreted as Escape. Enhanced CSI-u text keys are decoded as text.

Artwork and duration helper processes are detached from the interactive terminal:
their stdin is closed and they have no controlling TTY. Chafa runs with terminal
probing disabled, polite output and animation disabled. Native image placement
still happens on the UI thread. Completing a cover render must never read user
keystrokes or restore a different terminal input mode while search is active.
