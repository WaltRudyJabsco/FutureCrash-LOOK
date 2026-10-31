# 8.21.2 — Quiet Wayland clipboard capture

Bundle/node/Albert integration **8.21.2**; LOOK **4.68.2**.

Repeated wl-paste reads can create temporary focus-stealing surfaces on GNOME,
causing desktop-wide pulsing and menu dismissal. Automatic Wayland capture now
uses change events only. Unsupported desktops fail once per session and report
unavailable instead of polling or silently using XWayland. Book-reader return
also avoids unsolicited Wayland reads.

Use `lk clip add` or a in the shelf for an explicit one-shot capture, including
when automatic capture is off. Existing history and capture preferences survive
upgrades. macOS and native X11 behavior is retained.

Regression tests cover event delivery, Unicode/multiline text, sensitive/empty
states, unsupported desktops, opt-out, and absence of automatic clipboard reads.
Native GNOME visual behavior requires owner verification; the confirmed trigger
stopped when automatic capture was disabled. This release retains the Latin and
Wiki prompt repairs from 8.21.1.

Validation: 145 affected tests passed; generated command reference, shell syntax
and installer dry-run checks passed.
