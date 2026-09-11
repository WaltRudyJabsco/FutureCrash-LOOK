# 1.4.1 — LOOK prompt input fix

- Fixes doubled characters in LOOK's character-at-a-time prompts by using silent raw reads.
- `lmk` ambiguity selection is now immediate single-key input: `d`, `f`, or Esc.
- Parent-path confirmation is now immediate `y` / `n`.
- No Enter is required for these choice prompts.
- General LOOK text prompts retain character editing without duplicate echo.

Versions:
- Future Crash + LOOK 1.4.1
- LOOK 3.7.1
- Future Crash 1.0.0
