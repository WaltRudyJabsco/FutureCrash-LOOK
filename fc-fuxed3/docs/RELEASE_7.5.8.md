# 7.5.8 — FILTER FRAME

A focused LOOK filter/navigation repair from recovered 7.5.7 truth.

- Filter query changes reset selection to the first visible match instead of carrying an invisible prior index into a new result set.
- Up/Down navigation in filter mode remains synchronized with the highlighted row; Enter activates exactly the highlighted path.
- Native Kitty/iTerm/Sixel image payloads are no longer concatenated beside ordinary text rows.
- Pixel previews get a dedicated bounded bottom viewport above the footer, using Chafa view sizing and bottom/center alignment.
- Embedded side-by-side previews use composable Chafa symbol rows only.
- LOOK directory header and filter status remain visible while filtering.
