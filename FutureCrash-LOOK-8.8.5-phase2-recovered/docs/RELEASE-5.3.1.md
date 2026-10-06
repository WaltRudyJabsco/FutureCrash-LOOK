# 5.3.2 — Decision Interaction

This release closes the first interaction gaps found in the 5.3.0 Decision Plane.

## Terminal + Signal

`lk fabric ask "Use chapter-12?" yes no` now leaves an interactive prompt in a TTY. The prompt polls the same Fabric DecisionRequest shown by Signal, so answering from Safari releases the terminal immediately. Pressing Enter leaves the request pending and returns the shell.

## Media shorthand

`lk play "once in a lifetime"` is now an alias for `lk media play "once in a lifetime"`. It reuses the existing MediaSession/mpv worker semantics.

OpenJev remains optional and shadow-only.
