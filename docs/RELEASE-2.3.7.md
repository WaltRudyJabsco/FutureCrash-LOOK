# Future Crash + LOOK 2.3.7

Versions:

- Future Crash + LOOK: 2.3.7
- LOOK: 4.3.7
- Future Crash: 1.1.10

## `fc` is reserved for Zsh

LOOK no longer attempts to overload `fc`.

In Zsh, `fc` is the native history editor/manager. Shell plugins and paste/history machinery may call it with arguments. Bare `fc` can legitimately open the configured history editor.

Future Crash launchers are now:

```text
fcr
rst
future-crash
```

On shell reload, LOOK removes any stale `fc` function left by older releases and does not redefine it.
