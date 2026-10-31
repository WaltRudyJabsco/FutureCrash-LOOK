# 8.22.0 — Books discovery and browser narration

Bundle/node/Albert integration **8.22.0**; LOOK **4.69.0**.

Books adds Gutenberg discovery and asynchronous cover previews, with ASCII and
native image modes. Signal and Albert share an authorized Books reader through
`/books`, `read TITLE` and `continue reading`.

Audio is locally synthesized on the book owner into bounded cached AAC passages.
The browser plays it; owner speakers are untouched. Resume progress uses the
existing book content identity and owner, with browser offsets and paragraph
sharing from terminal read-aloud. Bookokrat's visual cursor remains independent.

No automatic package installation or book download is introduced. Owners need
a local voice and ffmpeg for browser narration. Narrow terminals preserve title
space; unsupported image terminals retain ASCII. See docs/BOOKS.md for controls,
setup and offline/concurrent-listener limits.

Validation: 175 affected tests passed, including authenticated book APIs,
byte-range audio, shared progress, cover extraction, terminal preview input and
idle rendering, reader/Latin regressions, fresh installation and managed updates.
A headless browser exercised shelf → paragraph → AAC playback → saved offset →
resume in a second mobile-sized tab. Real local voice-to-AAC generation and a
live Gutenberg cover through ASCII/native PNG preparation were also verified.
Generated command references, shell syntax and installer dry-run checks passed.
