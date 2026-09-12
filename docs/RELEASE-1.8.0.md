# Future Crash + LOOK 1.8.0

The filer now has a persistent cross-directory working set.

Mark paths with `Tab` or `A`, navigate with Enter and `<` (Shift-,), and continue selecting elsewhere. The set survives navigation. `C`, `M`, `R`, `Y`, clipboard actions, and `L` operate on the accumulated set; `X` clears it.

The status line is intentionally informative:

- `SELECTED · 3` — all three selected items are in the current view.
- `SELECTED · 7 / 3 HERE` — seven total selected paths, three in the current directory/view.

The local-only state is green; the cross-directory state uses an amber/yellow accent so an off-screen working set is difficult to forget.

Directories are stored as paths, not recursively expanded selections.

LOOK is 3.12.0. Future Crash remains 1.1.7.
