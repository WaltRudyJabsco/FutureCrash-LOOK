# Clipboard shelf

`lk clip` opens ten local text slots, numbered 1–9,0. Select a number to copy
and close; Shift-number or x removes a saved item. Enter previews; Esc returns.
Shift-Z opens the shelf from supported LOOK workspaces. Saved history stays on
this computer; s explicitly saves one clip as a normal synced note.
Shortcut keys and numbered slots use blue, with subdued gray action labels.
The command footer wraps to the terminal width.

- `lk clip on` requests automatic capture; `lk clip off` stops it without deleting history.
- `lk clip status` reports the preference and platform support.
- `lk clip add` (a in the shelf) explicitly adds the current clipboard, even with capture off.
- `lk clip clear` clears saved history without changing the system clipboard.

Automatic capture on Wayland uses `wl-paste --watch`, which requires the
compositor's data-control protocol. If unsupported, capture reports unavailable
and stops retrying for this session. After changing desktop support, `lk clip on`
explicitly retries. It never falls back to periodic clipboard reads. A manual
add reads once on request. macOS and native X11 retain their existing capture.

This avoids wl-paste's temporary-surface fallback, which can make GNOME's dock
pulse and dismiss menus when called repeatedly. Upgrades preserve the owner's
on/off preference and existing clips. No screen-control permission is required.

Upstream: [wl-clipboard manual](https://github.com/bugaevc/wl-clipboard/blob/master/data/wl-clipboard.1).

Mercury Mini opens this same local shelf with Ctrl-B; the Mercury web Clipboard
button reads its local saved clips when opened on localhost.
