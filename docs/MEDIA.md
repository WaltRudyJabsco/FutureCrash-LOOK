# Media

Media is a Fabric capability with endpoint-local presentation.

## Catalog, queue, playlist

The Fabric catalog answers *what media exists and on which node*. A queue answers *what this endpoint will play now*. A playlist is a saved queue. Keeping these separate prevents one endpoint's browsing or playback from unexpectedly changing another endpoint.

## LOOK Media Find

`lk media find QUERY` is both a catalog search and a lightweight playlist builder. Filtering follows LOOK's include/exclude grammar. `clash london` requires both terms; `clash \\live \\remix` requires `clash` while excluding rows containing `live` or `remix`.

Lowercase `q` is filter text, including in artist/album browsing. Escape exits; uppercase `Q` keeps its queue action.

Controls: Tab toggles the focused row; Shift-A selects/unselects every currently visible row; Enter or Shift-P plays selected rows (or the focused row); Shift-Q appends selected/focused rows to the queue; Shift-S saves selected/focused rows as a playlist; Shift-C clears selection; Shift-I shows identity/details; Esc clears the filter and then exits.

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

Artwork browsing currently uses embedded covers, image sidecars, or sibling-track
art from the same directory. Online Cover Art Archive downloads are performed by
matched CD imports; existing ordinary library albums are not automatically
searched online. Missing remote art can also reflect unavailable owner routes.

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

In `lk player`, press lowercase `v` to cycle Bars, Waves, Orbit, Tunnel, Stars, Plasma, then **Album Art**, followed by the normal player view. In `lk mp`, `v` opens the same player visuals. Album Art fills the available canvas with a centered ASCII cover while keeping track information and transport controls visible. Covers preserve their proportions for terminal cells, and remote covers load in the background. Missing artwork displays an availability message.
