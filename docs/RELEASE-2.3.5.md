# Future Crash + LOOK 2.3.5

Versions:

- Future Crash + LOOK: 2.3.5
- LOOK: 4.3.5
- Future Crash: 1.1.10

## Fix

Zsh already owns the command name `fc` for history management.

Older LOOK releases also used `fc` as a Future Crash shortcut. Shell/history tooling can legitimately execute commands such as:

```text
fc -p -a /dev/null 0 0
```

Because LOOK had replaced the builtin with a function, those history arguments were forwarded to Future Crash and appeared as:

```text
future_crash.py: error: unrecognized arguments: -p -a /dev/null 0 0
```

Pasting text could trigger history machinery, making the error look paste-related.

## Resolution

LOOK no longer defines `fc`.

On reload it explicitly removes any stale LOOK `fc` function:

```zsh
unalias fc 2>/dev/null
unfunction fc 2>/dev/null
```

which exposes Zsh's native builtin again.

Future Crash launchers are now:

```text
future-crash
rst
fcr
```

`fcr` replaces the old short `fc` alias/function.

Future Crash remains strict about unknown command-line arguments.
