# Future Crash + LOOK 2.4.0 — Settings control room

Versions:

- Future Crash + LOOK: 2.4.0
- LOOK: 4.4.0
- Future Crash: 1.1.10

## A human-facing settings surface

LOOK now has one obvious answer to:

> Where do I change that?

```text
lk settings
```

The control room is searchable. Typing narrows all settings immediately, including by plain-language concepts that may not appear in the command name.

Examples:

```text
memory
video
GPU
safe
downloads
sound
shortcuts
```

Or enter prefiltered:

```text
lk settings memory
lk settings video
lk settings gpu
```

## Layout

The selectable row shows:

```text
CATEGORY   Setting name   current value
```

The preview pane explains what the highlighted item does before changing it.

The header provides a compact status strip:

```text
model … · access … · memory … · shortcuts …
```

The searchable registry covers:

- AI model, host, access, thinking, think display, personality, web key
- AI performance/GPU telemetry and model benchmark
- Living Memory and manual compaction
- file grants and shell shortcut policy
- preferred desktop apps
- Tailscale/Ollama sharing
- sound and motion feedback
- portable profile
- Doctor and versions

## Submenus

File access now provides a small menu for:

```text
Personal folders
Add grant
Remove grant
Inspect grants
Clear grants
```

Preferred apps provide a category picker for:

```text
browser
editor
image
pdf
video
audio
```

Shortcut policy can be switched between `polite` and `force` from settings.

## One source of truth

The control room does not maintain a parallel settings database. It calls the same functions used by direct commands.

For example, changing Thinking in `lk settings` and running:

```text
lk thinking adaptive
```

modify the same configuration.

This keeps commands useful for scripting and muscle memory while making command memorization unnecessary for ordinary configuration.
