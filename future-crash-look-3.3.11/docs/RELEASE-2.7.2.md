# Future Crash + LOOK 2.7.2

A surgical Future Crash navigation fix.

```text
normal shell:
  future-crash / rst / fcr / fc → launch Future Crash

Future Crash escaped shell:
  future-crash / rst / fcr / fc → exit child shell → resume existing Future Crash
```

No nested Future Crash process is created. `exit` and Ctrl-D still work normally, but the named Future Crash commands now provide the clearest intentional way back.
