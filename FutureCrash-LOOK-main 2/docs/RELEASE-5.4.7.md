# 5.4.7 — Media Endpoint + Dash Input Hygiene

Signal browser playback is now a transactional Fabric endpoint handoff. **This Device / This iPhone** claims the active media card immediately, Safari receives range-capable audio incrementally instead of waiting for a whole-track proxy buffer, and failed playback restores the source-node selection without stopping it.

Dash now treats beacon/light/RGB/pulse records as renderer effects rather than semantic RECENT activity. Terminal ANSI escape sequences (including arrow-down `ESC [ B` and mouse/scroll reports) are consumed before single-key dispatch, and beacon key repeat is rate-limited.
