# Future Crash + LOOK 2.2.0

Versions:

- Future Crash + LOOK: 2.2.0
- LOOK: 4.2.0
- Future Crash: 1.1.9

## Terminal ownership

The terminal/tab title is now a lightweight owner indicator:

```text
● LOOK
● LO
● FUTURE CRASH
```

When control returns to Zsh, the title becomes:

```text
LOOK · <current-folder>
```

The indicator uses standard OSC title escapes and does not alter prompt content.

## Undo history

`lk undo` remains strict: only the newest transaction may be reversed, and divergence causes a refusal.

New commands:

```text
lk undo list
lk undo skip
```

`lk undo list` classifies active records as READY or BLOCKED and explains why.

`lk undo skip` is intentionally conservative:
- only the newest record may be skipped;
- it must already be BLOCKED;
- skipping changes only undo history, never the filesystem;
- the skipped record is retained in a small diagnostic history.

This lets the user explicitly abandon a divergent transaction and reach older undo history without LOOK guessing.

## File execution correctness

A failed mutation tool receipt can no longer be followed by a prose success claim. If a requested filesystem mutation has no successful receipt, LO reports the failure.

Common home-folder names in creation requests are normalized:

```text
"make x.html in the Downloads folder"
→ ~/Downloads/x.html
```

If that canonical destination lies outside the starting WORKSPACE boundary, the operation is refused cleanly instead of silently creating the file in the current directory.
