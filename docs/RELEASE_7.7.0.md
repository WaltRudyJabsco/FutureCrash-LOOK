# 7.7.1 — PREVIEW VIEW

Parent: 7.6.4 — SIMPLE PREVIEW.

Preview View is a second presentation of LOOK's existing filtered working set, not a second pager. Press `V` while filtering to use the content area for the current file preview. Arrow/J/K navigation changes the same current item; Space/Tab changes the existing marked set; existing file actions therefore retain LOOK's normal marked-set-first semantics. `V` or Esc returns to the filtered list without discarding the filter, current item, or marks.

This release intentionally retains the 7.6.4 renderer contract: image/PDF previews are ordinary synchronous Chafa symbol rows. No Kitty/iTerm/Sixel graphics protocols, preview workers, timers, deadlines, or asynchronous terminal painting are present in LOOK.
