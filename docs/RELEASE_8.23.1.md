# 8.23.1 — Wiki research links in Notes

Bundle/node/Albert integration **8.23.1**; LOOK **4.70.1**.

Notes accepts wiki: article links. Press c in an LK Wiki article to copy a labelled
Markdown reference, including the current live source or saved owner/archive.
The existing Notes link helper accepts it; selecting the rendered label opens
LK Wiki in the terminal. Escape returns directly to the note.

Missing pinned archives and invalid/ambiguous targets fail clearly. No protocol
handler, shell execution, archive download or silent source change is introduced.
All live Wiki, colored-link and image features from 8.23.0 are retained.

Validation: 400 affected tests passed, including all Notebook regressions, Wiki
source/link/image behavior, literal opener argv, direct return, pinned editions,
installer and managed updates. Generated references, shell syntax and installer
dry-run checks passed.
