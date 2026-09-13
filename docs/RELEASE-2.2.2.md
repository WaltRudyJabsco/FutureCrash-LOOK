# Future Crash + LOOK 2.2.2

Versions:

- Future Crash + LOOK: 2.2.2
- LOOK: 4.2.2
- Future Crash: 1.1.9

## Fix

Older LOOK releases installed aliases such as `lo`, `fc`, and `rst`. Newer releases use functions so they can manage terminal ownership titles and cleanup.

On `rb` / `exec zsh`, Zsh could still have the old aliases active while sourcing the new profile. Zsh performs alias expansion during parsing, producing errors such as:

```text
defining function based on alias `lk'
parse error near `()'
```

The LOOK profile now executes:

```zsh
unalias lk lo fc rst commands 2>/dev/null
```

before any same-name function definitions in the reload section.

No other behavior changes.
