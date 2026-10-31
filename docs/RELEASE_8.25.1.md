# 8.25.1 — Persistent Words desk

Bundle/node/Albert integration **8.25.1**; LOOK **4.72.1**.

Bare `lk words` now opens a dedicated persistent terminal desk with input active,
instead of the generic file pager. Type a word and Enter; Escape leaves input for
results/actions. From results, `/` edits the current query and 1–5 select Meaning,
Synonyms, Antonyms, Spelling and Patterns. Tab cycles views. Follow a thesaurus or
pattern word with Enter and return with `b`. Related alternatives are explicitly
labelled separately from direct synonyms.

Spelling omits ordinary recognized words. Select a suggestion and Enter to apply
it to the working text, then `c` copies that text. Original documents stay intact.
`y` copies a selected word/entry to the system clipboard and LK Clip; `p` pastes
and Z/editor Ctrl-Y inserts a clip. Longer pasted text selects Spelling. Bracketed
paste is literal text, with Unicode preserved and terminal controls escaped.

`W` opens an adjacent shell pane from results, with the existing terminal-owned
focus/close shortcuts. While editing, uppercase letters and digits remain input.
Narrow panes get compact controls with `?` help; the desk resizes and wraps its
content. Queries run asynchronously after submission, so input and Escape do not
wait for dictionary or remote work. Setup remains explicit and confirmed.

Cited WordNet examples can contain structured author/text records. Normalize
these at the data boundary so entries such as “obtuse” display without crashing.
The existing offline datasets and user vocabulary are preserved.

Validation: final affected regression suite **608 passed**. A real PTY exercised
bare `lk words`, typed “obtuse,” switched to synonyms and exited cleanly without
opening the file browser. Tests also cover small/wide frames, spelling application,
clipboard safety, panes, input modes, Escape during pending work and cited examples.
Generated references, shell syntax, installer dry-run and diff checks passed.
