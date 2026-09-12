# Future Crash + LOOK 1.6.14

This release closes a reliability gap between *talking about* host operations and actually performing them.

When the operator explicitly asks LO to create, write, copy, move, rename, edit, or remove local files, LOOK now requires a filesystem mutation tool call before a success report is accepted. A prose-only completion gets one silent retry with a tool-required instruction. If the model still fails to execute a tool, LOOK reports that no filesystem mutation occurred.

Workspace also gains read-only process, listening-port, and compact system inspection tools. Arbitrary command execution remains reserved for Power/Unsafe.

LOOK is 3.10.3. Future Crash remains 1.1.7.
