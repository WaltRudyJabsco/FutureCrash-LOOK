# 8.10.2 — terminal ownership and command help

- Runs Future Crash's shared LO turns in an isolated worker process, preventing
  LO's stdout capture and readline initialization from taking over the TUI.
- Restores immediate non-echo input if terminal settings drift. Recovery preserves
  queued input and avoids waiting for terminal output to drain.
- Keeps Ask/answer views closed after Escape when late replies or host receipts arrive,
  matching the workstation behavior. Enter on an empty answer view is harmless.
- Prevents background subprocesses from inheriting the live terminal input.
- Adds H / ? notebook help explaining capture, file, done, remind, delete, sync,
  and the difference between a due date and an alert. Expands lkn --help.
- Adds generated offline command help: lk COMMAND --help and lk help COMMAND,
  including Fabric flags and media/model/settings interface guidance.
- Makes navigation shortcuts honor --help rather than treating it as a folder query.
- Includes the LO worker and generated documentation in install and maintenance manifests.

Components: bundle/Albert 8.10.2; LOOK 4.57.2; Future Crash 1.2.4.
