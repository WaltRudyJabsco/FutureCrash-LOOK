# 5.7.0 — Fabric Content Search

The ordinary-file catalog now has a deliberately boring second layer: bounded deterministic text extraction plus SQLite FTS5. `lk scan` still owns discovery, but changed supported documents are now text-indexed incrementally; unchanged documents are not re-read. No embeddings, OCR, model calls, or hashing are part of indexing.

Supported content sources are plain text/Markdown, source and common config formats, HTML, DOCX, EPUB, and text-bearing PDFs. HTML/script noise is stripped, DOCX/EPUB use their standard ZIP/XML/HTML containers, and PDF extraction uses the already-installed Poppler `pdftotext` edge. Files over 4 MiB are left metadata-only and extracted text is capped at 256 KiB per file.

`lk find` now combines filename/path matches with FTS5 content matches and shows a short evidence snippet. Natural queries such as `lk find "where was that thing I wrote about GDP countermeasure happiness"` work without embeddings. Fabric search remains data-local: every node searches its own SQLite database and returns only bounded matches/snippets, never its full text index.

This establishes the cheap content layer for later artifact identity, data-local job placement, and optional semantic search without making those expensive mechanisms prerequisites.

