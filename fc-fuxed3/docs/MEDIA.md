# Media

Media is a Fabric capability with endpoint-local presentation.

## Catalog, queue, playlist

The Fabric catalog answers *what media exists and on which node*. A queue answers *what this endpoint will play now*. A playlist is a saved queue. Keeping these separate prevents one endpoint's browsing or playback from unexpectedly changing another endpoint.

## LOOK Media Find

`lk media find QUERY` is both a catalog search and a lightweight playlist builder. Filtering follows LOOK's include/exclude grammar. `clash london` requires both terms; `clash \\live \\remix` requires `clash` while excluding rows containing `live` or `remix`.

Controls: Tab toggles the focused row; Shift-A selects/unselects every currently visible row; Enter or Shift-P plays selected rows (or the focused row); Shift-Q appends selected/focused rows to the queue; Shift-S saves selected/focused rows as a playlist; Shift-C clears selection; Shift-I shows identity/details; Esc clears the filter and then exits.

## Albert

A Fabric media result may contain a complete queue. Albert retains that queue, displays the current position, advances automatically at track end, and provides previous/next/clear controls. A later audio play result replaces the earlier Albert audio queue.

Albert stores `{node,id}` for catalog items. At playback time it requests `/api/media/ticket`, assigns the returned same-origin `/api/media/audio` URL to the native media element, and lets the facade proxy Range requests to Fabric. The native `<audio>` element remains the playback engine; visualization is presentation-only.
