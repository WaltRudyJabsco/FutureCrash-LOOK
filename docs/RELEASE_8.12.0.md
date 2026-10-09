# 8.12.0 — Inline Notebook

Enter opens notes, tasks and reminders in a boxed Markdown view. Arrow keys
and Space scroll; E edits the body, Enter saves, and Shift-Enter/Ctrl-J adds
a newline. Escape cancels an edit or returns from the view. V opens the same
Markdown document in the configured full editor (Neovim by default when available).

Named entries such as `lkn To Do` reopen this view. Quick edits preserve titles,
reminder schedules, task status and project labels. Concurrent changes cannot
be overwritten: failed saves preserve the draft locally for recovery.

Bundle 8.12.0; LOOK 4.59.0; Future Crash remains 1.2.5.

Validation: 977 tests pass; real PTY edit/save/Escape smoke check passes.
Generated help, code-health, shell syntax and Python 3.10 parsing checks pass.
