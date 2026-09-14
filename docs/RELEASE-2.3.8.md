# Future Crash + LOOK 2.3.8 — Polite shell namespace

Versions:

- Future Crash + LOOK: 2.3.8
- LOOK: 4.3.8
- Future Crash: 1.1.10

## Three layers

### Canonical

```text
lk
lk detail
lk dirs
lk files
lk tree
lk recent
lk size
```

### Fast LOOK namespace

Always installed:

```text
lkl  detail
lkd  directories
lkf  files
lkt  tree
lkr  recent
lkz  size
```

These names deliberately carry the `lk` prefix and are treated as LOOK-owned vocabulary.

### Ultra-short convenience layer

```text
l
ll
ld
lf
lt
lr
lz
```

These are optional shell conveniences.

Default policy is `polite`: if a name already belongs to an alias, function, builtin, or executable, LOOK leaves it alone.

```text
lk shortcuts
lk shortcuts polite
lk shortcuts force
rb
```

`force` may replace an alias or function. It still does not replace a shell builtin or executable on PATH.

This means `/usr/bin/ld`, native `ls`, an installed `lf` file manager, and similar established commands remain reachable normally.

## Retired global aliases

LOOK no longer installs:

```text
lsd
lsf
lc
```

`lsd` in particular is an established modern `ls` replacement.

## Principle

LOOK owns one broad namespace: `lk`.

Fast aliases are conveniences, not prerequisites. Every filesystem view remains available under `lk ...` even when a short alias is unavailable because the user's shell already owns that name.
