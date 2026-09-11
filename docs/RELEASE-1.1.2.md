# 1.1.2 — installer platform detection fix

Fixes `install.sh: OS: unbound variable` in the optional Terminal Experience stage.

The terminal setup now derives its own platform value with `uname -s` instead of depending on a global installer variable.

No runtime, memory, capability, LOOK, Future Crash, or AI behavior changed.
