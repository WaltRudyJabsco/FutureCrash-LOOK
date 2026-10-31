# 8.23.2 — Stable Wiki reading position

Bundle/node/Albert integration **8.23.2**; LOOK **4.70.2**.

Adding hint codes changes wrapping, so preserving a wrapped line number moved
the user's reading position. Track the source paragraph and character near the
viewport center, excluding inserted hint text, and remap that anchor on layout
changes. Repeated toggles retain the original anchor until the user scrolls.
Normal and hint footers reserve the same height; back history uses source anchors.
Viewport start/end boundaries can still clamp the view.

Tests cover long Alexandria-style content, Unicode/cell wrapping, three widths,
repeated no-drift toggles and equal footer height. No inline-image layout changes
are part of this repair; the existing image gallery remains available.

Validation: final affected suite 404 passed. An existing media-helper timing
check passed on isolated retry and the subsequent clean full run. Generated
references, shell syntax and installer dry-run checks passed.
