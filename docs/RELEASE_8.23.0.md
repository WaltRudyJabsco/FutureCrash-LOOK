# 8.23.0 — Live Wiki, link ink and article images

Bundle/node/Albert integration **8.23.0**; LOOK **4.70.0**.

Followable article text stays accented while reading; f adds hint codes beside
those same links. The shelf puts Live Wikipedia above saved references. Selecting
it or using v explicitly changes source. Live mode uses the official English
Wikipedia REST API without requiring a Fabric owner or libzim; saved mode never
fetches live article text or pictures implicitly.

Add an asynchronous image gallery with ASCII/native rendering and source links.
Saved pictures must exist in the selected archive; a no-pictures archive cannot
provide photographs. Existing archives, reader setup and user configuration are
preserved. Cache state and Wikipedia attribution remain visible.

See docs/BOOKS.md for source flags, gallery controls, cache and image limits.

Validation: 197 affected tests passed, including exact link spans, Unicode/cell
wrapping, live-entry selection, cache/redirect limits, no-network saved mode,
real ZIM image extraction and installer/update checks. Live Architecture search,
article photos, ASCII rendering and native PNG preparation were also verified.
Generated references, shell syntax and installer dry-run checks passed.
