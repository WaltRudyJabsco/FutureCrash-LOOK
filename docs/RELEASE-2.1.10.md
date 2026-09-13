# Future Crash + LOOK 2.1.10 — File destination fidelity

Versions:

- Future Crash + LOOK: 2.1.10
- LOOK: 4.1.10
- Future Crash: 1.1.8

## Fixed

`copy_path` and `move_path` referenced a missing `_final_destination` helper. A move attempt could therefore crash the entire LO process with `NameError`. The helper is restored through LOOK's canonical destination planner and filesystem tool exceptions are contained at the tool boundary.

## Destination contract

If the user names a destination folder, the tool path must preserve it.

From workspace `~`:

```text
make boilerplate3.html in Downloads
→ Downloads/boilerplate3.html
```

If `~/Downloads` is outside the current WORKSPACE boundary, LO reports that boundary instead of silently creating `./boilerplate3.html`.

## Reveal

LO has a read-only `reveal_path` tool for “show me the file” requests.

Direct command:

```text
lk reveal PATH
```

macOS uses Finder reveal. Linux opens the containing folder through `xdg-open`. Windows uses Explorer/select where available.

## Shell navigation

The packaged Zsh profile no longer aliases `cd` to zoxide.

```text
cd  → real builtin cd, with Zsh correction suppressed
z   → zoxide fuzzy/history navigation
```

This ensures a newly downloaded/extracted directory can always be entered by exact path before zoxide has learned it.
