# 8.20.0 — Reading and offline knowledge

Bundle/node/Albert integration **8.20.0**; LOOK **4.67.0**.

Bookokrat gains missing Shift-arrow paging/end defaults. Existing custom bindings
and settings are preserved, with a backup on first change. Space commands remain
sequential taps. Reader copying continues to the system clipboard and is captured
by LK Clip only when capture is enabled; Shift-P opens the shelf from Books.

Books adds a local read-aloud paragraph/chapter view: Enter starts, Space pauses,
s stops, v chooses an installed voice, Esc returns. Speech has its own local saved
position and process ownership. macOS prefers an installed British voice; optional
Piper setup provides an offline British neural voice. PDF speech requires extractable
text. See [Books](BOOKS.md).

`lk wiki` adds an offline Kiwix reference shelf and paired API. Choose the owner and
destination, install the isolated ZIM reader, then explicitly confirm a collection
and its size. Downloads support retained partial-file resume, HTTPS mirrors and
SHA-256 verification before publication. Search/articles work offline on the
archive owner; a remote owner still requires a reachable Fabric route. Readable
text and internal links are available in the terminal. See
[Offline references](OFFLINE-REFERENCES.md).

Setup and download workers are protected from managed update interruption. Existing
reader/media data, clipboard preferences and audio output routing remain intact.

Validation: 228 affected tests passed, including real Bookokrat Shift-arrow input
and shelf return, real ZIM creation/search/article reading, paired HTTP setup
confirmation, download resume/checksum/cancel handling, speech process ownership,
clipboard opt-in behavior and media input regression checks. A small official
Kiwix sample also passed download/SHA-256/offline-search checks; the selected
British macOS voice produced a verified audio file without speaker playback.
