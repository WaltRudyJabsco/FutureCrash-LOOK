# Future Crash + LOOK 6.2.4 — Good Listener

6.2.4 makes media language a shared edge contract rather than a collection of surface-specific conventions. Direct `lk play`, terminal LO, Signal, and routed Fabric playback classify requests before catalog lookup.

The four intended modes are:

- **selector** — `play a song`, `play any movie`, `play some music`; chooses from a media kind rather than searching for those words.
- **fuzzy** — `play mighty boosh mutants`; forgiving title/artist/filename lookup is the default for ordinary names.
- **literal** — quoted targets in LO/Signal or `lk play --exact ...`; deterministic lookup without semantic guessing.
- **clarify** — deictic/ambiguous language such as `play that movie` or close catalog races should ask or offer candidates rather than guess.

Filename matching now treats case, media extensions, underscores, dashes, slash-like punctuation, and repeated spacing as presentation differences. Ranking is dependency-free and confidence-gated: strong matches execute, close matches surface candidates, and weak matches remain failures. No catalog data is rewritten.

Shell quoting is intentionally not used as a literal-mode signal for direct `lk` commands because the shell removes quote characters before LOOK receives argv. `--exact` and `--literal` are the inspectable deterministic escape hatches.

Signal Window 1.10.4 carries literal/fuzzy mode through the Fabric route so browser and terminal semantics remain identical.
