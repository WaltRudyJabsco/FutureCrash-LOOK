# 6.7.2 · STAY AWAKE

Models may sleep; goals stay alive.

This release moves continuity out of chat prose and into a small persistent working-state layer. Active goals and unresolved slots survive LO process exits and are injected as authoritative context before inference. `lk brain` exposes the state; `lk brain clear` resets only working state, not durable memory.

The first production use is WEATHER/Home Base: when LO asks for a weather location and the operator answers `home`, an unknown home creates a distinct `home.location` slot. The next place both teaches home and resumes the original weather goal. Explicit forms such as `I live in Portland OR` and `remember that I live in Portland Oregon` synchronously rewrite the typed home atom. Once home is learned, locationless weather requests use it without asking again. Successful weather receipts close the persistent goal.

Memory gets a larger cheap reservoir without dumping it all into inference: 48 recent exchanges / 64k stored characters, a 14k recent-context budget, and larger bounded semantic retrieval. The rule remains: keep more, retrieve selectively.

This is intentionally not an always-thinking agent loop. Persistent activity is event/state driven: the daemon may remain awake, but expensive cognition wakes only when a goal has new input or work. Future background goals can build on the same state contract rather than inventing per-feature loops.
