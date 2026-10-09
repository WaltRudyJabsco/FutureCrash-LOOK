# 8.11.0 — reusable notebook and footer accents

- Accents Future Crash footer key tokens in cyan while retaining label colors,
  command wording, and layout.
- Shows note creation and latest-edit timestamps. Shift-F cycles sorting by
  updated, created, title, project, due/reminder, and type while retaining focus.
- Makes typing a title/project filter and `/` a full-text search toggle.
  Backslash-prefixed terms exclude matches in the active scope.
- Shift-T cycles all records, notes, tasks, and reminders.
- Reopens reusable notes by exact title or ID with plain `lkn To Do`; first use
  creates the note. Duplicate titles require a choice; `lkn new` forces capture.
- Accepts reminder durations with or without "in", common written quantities,
  standalone clock times, and optional "at" in named-day expressions.
- Updates notebook help and generated reference surfaces.

Components: bundle/Albert 8.11.0; LOOK 4.58.0; Future Crash 1.2.5.
