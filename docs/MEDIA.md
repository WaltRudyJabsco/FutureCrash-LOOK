# Media

Media is a Fabric capability with endpoint-local presentation.

## Catalog, queue, playlist

The Fabric catalog answers *what media exists and on which node*. A queue answers *what this endpoint will play now*. A playlist is a saved queue. Keeping these separate prevents one endpoint's browsing or playback from unexpectedly changing another endpoint.

## LOOK Media Find

`lk media find QUERY` is both a catalog search and a lightweight playlist builder. Filtering follows LOOK's include/exclude grammar. `clash london` requires both terms; `clash \\live \\remix` requires `clash` while excluding rows containing `live` or `remix`.

Controls: Tab toggles the focused row; Shift-A selects/unselects every currently visible row; Enter or Shift-P plays selected rows (or the focused row); Shift-Q appends selected/focused rows to the queue; Shift-S saves selected/focused rows as a playlist; Shift-C clears selection; Shift-I shows identity/details; Esc clears the filter and then exits.

`/` starts search editing. Enter or Esc finishes editing while keeping the filter.
Arrows, Tab, and selection actions work directly on the filtered results, including
while editing. A subsequent Esc clears the filter; another exits.

In `lk mp`, Shift-A likewise selects/unselects all visible results and Shift-C clears
marks. Shift-B adds marked results (or the focused row) to the queue; Shift-Q shows
the queue. Enter plays marked results or the focused row after search editing ends.

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
