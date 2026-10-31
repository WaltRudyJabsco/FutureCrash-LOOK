# 8.18.0 — Bookshelf

Bundle, Albert integration and node **8.18.0**; LOOK **4.65.0**.

Adds **lk books / lk bk**: a separate Fabric EPUB/PDF shelf over configured books
folders, copy-based imports, metadata edits, reading states, custom shelves and
manual reading-position labels. Existing Notes file/Fabric links connect books
to projects. Remote opening verifies a local cache copy before launching the
configured/system reader; explicit offline copies live in the local books folder.

Project Gutenberg search uses its official OPDS navigation and acquisition feeds.
Selecting a result requires confirmation before downloading to the chosen owner.
Direct public HTTPS EPUB/PDF downloads also work. Document bytes and source files
are preserved; this release does not build a new reader or track external reader
progress. See [Books](BOOKS.md) for commands and controls.

Adds **Orrery**, an inclined clockwork solar system, and **Phosphor Rain**, falling
trails with expanding ripples. Both are deterministic ambient animations and join
Cycle; they do not claim to measure audio PCM.

Includes fresh-install module shipping, shell completion, generated help/man
updates and a shelf UI that reuses existing path-picker, palette and pane tools.

Validation: 147 focused bookshelf, HTTP/range, visualizer, native-preview, catalog
and release/installer regressions passed. A real Gutenberg acquisition into an
isolated temporary shelf returned Pride and Prejudice by Jane Austen, verified
its EPUB bytes and registered one document. Generated command-reference checks,
shell-completion syntax and the unified installer dry run passed.

Trusted nodes retry advertisement discovery at the known-node interval after a
restart, instead of entering the initial unknown-device backoff. Unknown/unpaired
devices retain the slower discovery interval. This reduces temporary missing-peer
states during coordinated updates without changing trust or authorization.
