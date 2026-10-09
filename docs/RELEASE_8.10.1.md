# 8.10.1 — notebook interaction fixes

- Clears the screen on entering LKN and erases old line tails during repaint.
- Adds multiline quick capture: Enter saves, Shift-Enter inserts a newline,
  Escape cancels, and Ctrl-J/Alt-Enter work as terminal-compatible alternatives.
  Modified-key reporting and raw input are scoped to capture and restored on exit.
- Adds explicit LO notebook list/read tools and clarifies empty search behavior.
- Answers simple requests to list notes or read the first/second note directly
  from saved records, using the same newest-updated-first order as LKN.
- Preserves UTF-8 input in the shared key decoder.

Components: LOOK 4.57.1; Future Crash 1.2.3; bundle/Albert 8.10.1.
