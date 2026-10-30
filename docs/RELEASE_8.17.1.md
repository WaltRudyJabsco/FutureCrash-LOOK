# 8.17.1 — Reliable catalog refresh and stable previews

Bundle/Albert integration/Unified Node **8.17.1**; LOOK **4.64.1**.

A remote video could exist in the M3 Fabric catalog yet disappear from terminal
search because every catalog rebuild exceeded the terminal's three-second
request deadline. Expired snapshots now remain available during one background
refresh. A refreshing terminal snapshot is rechecked after three seconds rather
than retained for the normal 45-second cache interval. Cold starts can still
show a local fallback until the first remote snapshot finishes; Shift-R retries.

Each owner exposes an opaque catalog revision that changes with library or
curation edits, including renames that leave item counts unchanged. Peers check
that small revision before transferring an unchanged full catalog. Existing
item identities are preserved. Older nodes without revision support still work
through full catalog transfers; manual refresh remains available.

Native previews retain one prepared image across text redraws. Returning to the
same image/geometry restores it before waiting for input, avoiding the repeated
ASCII/native transition caused by availability or duration updates. Source,
mtime or geometry changes prepare a new image; obsolete work never paints the
wrong selection. ASCII remains the fallback when native rendering is unavailable.

No commands or shortcuts changed. Reopen existing Media Find/MP/TV screens after
updating to load the new rendering behavior.

Validation: catalog revision/compatibility tests, slow-refresh concurrency tests,
local HTTP transport, native-image redraw/reselection and controlling-terminal
input regressions. The focused run had 219 passes and one timing-sensitive
helper-trace failure; all four controlling-terminal cases passed on isolated
rerun. Command-reference consistency and the installer dry run also passed.
