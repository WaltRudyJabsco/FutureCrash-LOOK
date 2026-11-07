# Clipboard images and files

`lk clip` keeps ten recent items. Text stays text; images and copied files are
private snapshots, limited to one file and 3 MiB per item. Copy a file in Finder
or a Linux file manager, or copy an image, then use `lk clip add` or `a` in the
shelf. Enter previews an item; its number restores it to the system clipboard.
Text editors only insert text items.

Automatic capture on Mac and X11 includes supported images and files. Wayland
background capture remains text-only where data-control is available; use Add
for images and files. Unsupported Wayland desktops are never polled.

`lk clip share on` also publishes new attachments to trusted Fabric peers.
Sharing remains opt-in and existing history is not exported. Copies carry actual
bytes, so a Mac path is not mistaken for a Linux path. Sources must be online;
refresh with `r`. `share off` withdraws published items, but cannot retract copies
already recalled on another computer. The Notes-backed `s` action remains text-only.

`lk print clip` reviews the current item. If unavailable or unsupported, it opens
the ten-item picker. Text and Markdown use receipt typography. PNG/JPEG images
show a terminal preview and offer rotation, style, copies and paper allowance.
PDFs require a page range and a document printer. The final print confirmation
is always required. Unsupported files remain in the shelf and are never executed.

Attachments use a versioned envelope in the existing private clipboard database.
All peers need this update to display and recall attachments. Recalled attachments
are materialized under the private clipboard `recalled` directory so file URLs
remain usable after closing the shelf. These files are not canonical documents.
