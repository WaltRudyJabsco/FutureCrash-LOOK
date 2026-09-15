# Future Crash + LOOK 2.8.2

Command ownership cleanup.

```text
f    Future Crash (optional force-mode shortcut)
ff   LOOK fuzzy finder
fcr  canonical Future Crash convenience
fc   native Zsh history builtin, always
```

Earlier releases installed the new `f` shortcut and later redefined `f()` as the old fuzzy finder. That startup-order conflict is removed.

LOOK also actively restores native `fc` when sourcing, cleaning up older force-mode installations that may have shadowed or disabled the Zsh builtin.
