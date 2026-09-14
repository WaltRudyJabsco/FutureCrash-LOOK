# Future Crash + LOOK 2.5.1

Versions:

- Future Crash + LOOK: 2.5.1
- LOOK: 4.5.1
- Future Crash: 1.1.10

## UNSAFE means one thing

Before 2.5.1, LO had two independent permission systems:

- UNSAFE disabled shell-command confirmation.
- filesystem tools still enforced workspace/path grants.

That made this contradictory:

```text
access · UNSAFE
...
LO FILE ACCESS
wants WRITE ~/Downloads/file.txt
```

In 2.5.1 the filesystem transaction receives the active LO access profile.

### Behavior

```text
WORKSPACE
→ current workspace + explicit grants

POWER
→ current workspace + explicit grants
→ shell commands available under POWER confirmation rules

UNSAFE
→ unrestricted filesystem paths under the current user account
→ unrestricted shell command execution for the session
```

UNSAFE still requires the session-level confirmation when entered. It does not prompt again for each filesystem path.

The profile is scoped to each filesystem transaction and restored afterward.
