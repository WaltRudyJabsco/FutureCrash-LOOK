# Future Crash + LOOK 2.3.6

Versions:

- Future Crash + LOOK: 2.3.6
- LOOK: 4.3.6
- Future Crash: 1.1.10

`fc` is now a compatibility dispatcher:

```zsh
fc() {
  if (( $# == 0 )); then
    _future_crash_owned
  else
    builtin fc "$@"
  fi
}
```

This preserves both behaviors:

```text
fc
→ launch Future Crash

fc -p -a /dev/null 0 0
→ native Zsh history builtin
```

So normal paste/history machinery cannot accidentally launch Future Crash, while the short launcher remains available.
