# LOOK Saver

`lk saver` opens the terminal picker. `lk sv` starts the saved selection on all
attached displays by default. Escape, q, or a click dismisses all saver windows;
the terminal session and music playback continue. This is an ambient screensaver,
not a password lock or system sleep command.

## First use

Run `lk saver setup` once on each desktop. It installs the pinned
`PySide6-Essentials==6.10.3` graphics runtime in
`~/.local/share/look/saver-runtime`, separate from system Python. The picker’s
**G** action offers the same setup with an installation summary and confirmation.
The picker, text listing, help, and settings work without Qt installed.
Setup needs internet access; playback of these procedural scenes does not.
Linux requires a graphical desktop session (Wayland or X11), and may require
Qt platform libraries from the system package manager if they are missing.

## Commands

```sh
lk saver                         # picker and settings
lk sv                            # start saved selection
lk sv cycle                      # cycle enabled scenes
lk sv "Dune Sea"                  # names also accept dune-sea
lk saver start "Harmonic Ink"     # readable launch alias
lk sv --display all              # one window per attached display
lk sv --display current          # display under the pointer at launch
lk sv --matching                 # same scene, phase and palette
lk sv --independent              # each display gets its own sequence
lk sv --palette mercury          # use Mercury's colors
lk sv --no-invert                # no inverted color pairs
lk sv --interval 30              # 30 seconds per scene; range 5–600
lk sv "Stars" --preview          # small graphical preview window
lk sv --preview --seconds 10     # preview that closes automatically
lk saver --palette mercury --save # save without launching
lk saver list                    # names for scripts and completion
```

Launch overrides do not change preferences unless `--save` is supplied. Settings
are stored atomically in `~/.config/look/saver.json`; the music player's enabled
visualizers are independent. All procedural player scenes are available. Album
Art is omitted because the saver has no dependency on an active music session.
These are ambient animations, not measurements of audio levels.

## Picker keys

| Key | Action |
|---|---|
| Arrows, Page Up/Down, Home/End | Select a scene |
| Shift+arrows | Page or jump to first/last scene |
| Space | Enable/disable selected scene for Cycle |
| P | Open graphical preview; return to picker on dismissal |
| Enter | Start selected scene with the current settings |
| A | Save settings and stay in the picker |
| D | All displays / current display |
| M | Matching / independent displays |
| C | Cycle palettes |
| I | Toggle occasional inversions |
| - / + | Decrease/increase cycle interval |
| G | Set up isolated graphics runtime |
| q / Escape | Leave picker without saving pending changes |

Colors and inversions change at scene boundaries, never each frame. Rendering is
bounded to 20 frames per second and a 240×80 character grid per display. Text is
painted directly with a monospace font, not enlarged from terminal screenshots.
Matching displays use the same scene state even if a display skips a repaint.
All-display mode responds to display additions and removals. Current-display
mode falls back to a remaining display if its original display is disconnected.

Automatic idle activation, native password-lock integration, audio-reactive
analysis, and multi-panel control-room compositions are not part of this release.
