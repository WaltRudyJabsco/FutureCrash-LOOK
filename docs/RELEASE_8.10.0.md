# 8.10.0 — replicated notebook and responsive workstation

- Adds `lkn`, `lk notes`, `lk tasks`, and `lk reminders` over one Markdown notebook.
- Exchanges immutable revisions with paired nodes, preserving offline conflicts
  and deletion markers. Captures, filing, editor updates, and task completion
  keep stable record IDs.
- Delivers due reminders through the Fabric beacon and Albert/Signal cards,
  including shared Done/Snooze updates and overdue catch-up.
- Moves Future Crash host operations off the keyboard loop. Escape closes the
  workstation while an operation is pending; its eventual receipt is preserved
  without reopening the workstation or continuing unattended tool proposals.
- Installs both notebook modules and updates the generated command reference.
- Normalizes macOS FLAC MIME metadata and lists the filesystem root once when
  a mounted-volume alias resolves to `/`.

Components: LOOK 4.57.0; Future Crash 1.2.3; bundle/Albert 8.10.0.
