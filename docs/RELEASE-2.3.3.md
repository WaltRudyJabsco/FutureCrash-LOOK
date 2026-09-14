# Future Crash + LOOK 2.3.3 — Desktop bridge + agent cleanup

Versions:

- Future Crash + LOOK: 2.3.3
- LOOK: 4.3.3
- Future Crash: 1.1.10

## Agent-loop cleanup

LOOK now distinguishes model capability from host capability.

If Ollama reports that a selected model does not support tools, LOOK does not send tool schemas to that model. This avoids HTTP 400 failures while keeping ordinary chat/thinking available.

POWER/UNSAFE still retain LOOK's narrow host-side safe-inspection repair. When that repair runs, the following model pass is explicitly final-answer-only and receives no tools, preventing redundant inspection loops.

## Compact thinking

The three-line compact thinking renderer now redraws exactly the previous number of lines and clips content to terminal width. This fixes duplicated or concatenated thinking fragments after the rolling window reaches full height.

## Desktop bridge

The terminal is the control surface, not the boundary of the computer.

Direct commands:

```text
lk open PATH
lk preview PATH
lk reveal PATH
lk apps
```

LO tools:

```text
open_path
preview_path
reveal_path
```

Semantics:

- **open** — launch the artifact in a graphical/default/preferred application.
- **preview** — quick external preview; macOS prefers Quick Look.
- **reveal** — locate the path in Finder/file manager.

### App preferences

Categories:

```text
browser
editor
image
pdf
video
audio
```

Examples:

```text
lk apps video vlc
lk apps video mpv
lk apps pdf system
lk apps editor code
```

`system` is the default for every category.

On macOS, custom application names are passed through `open -a`. On Linux, preferred executable names are resolved from PATH; otherwise `xdg-open` handles the system default. Windows uses its file associations when no override is configured.

No additional GUI application is mandatory. LOOK Doctor reports available system openers, Quick Look, terminal preview helpers, and detected VLC/mpv installations.

### Permission boundary

When LO opens/previews/reveals a path, normal LOOK read/path-grant rules still apply. A direct `lk open PATH` is an explicit user command and uses that path directly.
