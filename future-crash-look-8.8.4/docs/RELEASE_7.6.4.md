# 7.6.4 — SIMPLE PREVIEW

This is an intentional LOOK renderer rollback to the proven 7.5.7 pager. Native terminal graphics introduced after 7.5.7 are removed from LOOK. Image and PDF previews use Chafa symbol rows and are composed synchronously into the same filtered text frame as the file list.

## Invariants

- Normal browse has no side preview.
- Filter/selection owns one synchronous terminal frame.
- Image/PDF preview is ordinary text rows in that frame.
- No Kitty, iTerm2, or Sixel payloads.
- No preview timers, worker threads, generation counters, or asynchronous terminal painting.
- Legacy Auto/Graphics preferences normalize to ASCII on load.
