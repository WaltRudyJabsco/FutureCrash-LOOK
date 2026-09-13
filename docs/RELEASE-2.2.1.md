# Future Crash + LOOK 2.2.1

Versions:

- Future Crash + LOOK: 2.2.1
- LOOK: 4.2.1
- Future Crash: 1.1.9

## Workspace is now a default trust boundary

LO can request a path outside the folder where the session started. LOOK resolves the exact requested path first, then enforces access locally.

When access is missing:

```text
LO FILE ACCESS
  wants WRITE  ~/Downloads/example.html
  workspace    ~/Projects/current
  grant root   ~/Downloads

[A] once · [S] session · [P] always · [H] personal folders · Enter/Esc cancel
```

The model does not decide permission and cannot turn a denial into a different destination.

### Grant scopes

- **Once** — the complete current filesystem tool transaction only.
- **Session** — the granted directory for this LO process.
- **Always** — persistent local grant.
- **Personal** — persistent read/write access to existing `~/Desktop`, `~/Documents`, and `~/Downloads`.

Write grants imply read access. Read-only grants can be created explicitly.

### Management

```text
lk access
lk access personal
lk access add ~/SomeFolder write
lk access add ~/Reference read
lk access remove ~/SomeFolder
lk access clear
```

Persistent rules live in LOOK's private state directory and are written mode 0600.

### Safety invariants

- The current workspace remains trusted by default.
- Missing grants in background/noninteractive jobs fail closed.
- Cancel means no filesystem mutation.
- Destination denial never falls back to the current directory.
- Existing remove confirmation and undo journaling remain intact.
