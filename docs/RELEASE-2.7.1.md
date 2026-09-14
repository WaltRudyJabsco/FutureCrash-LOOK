# Future Crash + LOOK 2.7.1

A surgical shell-UX update.

## Force really means force

Default behavior remains polite:

```text
fc → Zsh history builtin
fcr → Future Crash
```

After:

```text
lk shortcuts force
rb
```

LOOK explicitly disables Zsh's `fc` builtin and installs:

```text
fc → Future Crash
```

Real executables remain protected.

## Stateful home

`lk home` no longer assumes optional shortcuts exist.

If aggressive aliases are active it can show:

```text
l look around   lo ask   lk inspect   lh home   fc Future Crash
```

If they are not active, it falls back to canonical truth:

```text
lk look around   lk o ask   lk inspect   lk home home   fcr Future Crash
```

The shell exports its live shortcut ownership state so LOOK can render the actual current environment.

`lh` itself is optional/collision-aware; `lk home` is canonical and always available.
