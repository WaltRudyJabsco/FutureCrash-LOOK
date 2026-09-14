# Future Crash + LOOK 2.7.7

A surgical Future Crash input/inference fix.

The Enter key mapping was correct. The failure was that `submit()` silently returned whenever Future Crash was already busy or considered Oracle offline.

Now:

```text
busy background Oracle call
→ operator presses Enter
→ request is visibly queued
→ current call finishes/times out
→ operator request dispatches automatically
```

Offline submits keep the typed text instead of discarding intent.

Future Crash also inherits LOOK's selected model, preventing a client from forcing a different model onto the shared 3090 and causing avoidable load/swap delays.
