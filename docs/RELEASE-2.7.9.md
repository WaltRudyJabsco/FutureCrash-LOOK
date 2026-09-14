# Future Crash + LOOK 2.7.9

Two related Zsh integration fixes.

## Reload/install parse safety

LOOK now clears names such as `rb` before defining functions. This prevents an older alias from being expanded while Zsh parses a new `rb()` definition.

## Safe `fc`

Zsh's `fc` is not merely a user-facing history command. ZLE/bracketed-paste code may call it internally with flags such as:

```text
fc -p -a /dev/null 0 0
fc -P
```

Shadowing that builtin with Future Crash caused pasted shell commands to be misrouted into `future_crash.py`.

LOOK no longer disables or replaces the builtin. In force-shortcut mode, only a user-entered interactive line consisting exactly of `fc` is rewritten to `fcr` by ZLE before execution.

So:

```text
typed `fc`      → Future Crash
internal `fc …` → native Zsh history builtin
```
