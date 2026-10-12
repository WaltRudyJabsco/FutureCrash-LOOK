# Media

Media is a Fabric capability with endpoint-local presentation.

## Catalog, queue, playlist

The Fabric catalog answers *what media exists and on which node*. A queue answers *what this endpoint will play now*. A playlist is a saved queue. Keeping these separate prevents one endpoint's browsing or playback from unexpectedly changing another endpoint.

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
or sound output works correctly.

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
then press E. Shared fields include artist, album artist, album and disc. One
selected track also offers title and track number. Return keeps each current
value; the final review shows the count and changes before saving. R refreshes
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
explicit compilation album artists remain intact. Each owner validates the
entire batch before writing, checks for stale metadata, and restores sidecars if
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
