# LOOK Saver

`lk saver` opens the terminal picker. `lk sv` starts the saved selection on all
attached displays by default. Space, Escape, or a click dismisses all saver windows;
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

On macOS, the saver covers displays with borderless windows and temporarily hides
the menu bar and Dock using application-local presentation options. It does not
create full-screen Spaces or change system preferences. Display geometry is
reapplied after presentation begins so the former menu-bar area is covered too.
Escape/click, timed dismissal, and interrupt restore the original presentation
options before closing the windows. Small previews retain normal window controls.

While running, **C** changes colors and **V** advances the visualizer on every
display. Matching displays remain matched; independent displays keep their own
sequences. V also works after launching a named scene, stepping into the enabled
scene list. Space or Escape dismisses; unrelated keys are ignored, and holding
C/V does not repeatedly cycle. Mouse movement does not dismiss; a click does.

## Cinematic scenes and Bridge palette

Flight Deck uses oversized block lettering, alternating inverse bands, fictional
readouts, and short deep-space captions. Signal Bloom pairs a slow radar sweep
with orbiting contacts. Both are available in the player visualizer picker as
well as the saver. Bridge adds charcoal, amber, pale green, and cool blue:

```sh
lk sv "Flight Deck" --palette bridge
lk sv "Signal Bloom" --palette bridge
lk terminal theme bridge
```

Flight Deck works offline with built-in captions. Optionally run `lk saver text`
to prepare a fresh set through the existing Fabric inference service. This is an
explicit, bounded request using a generic fictional-writing prompt; it sends no
files, notes, or listening history. Validated captions are saved in
`~/.config/look/saver-text.json` and read once by new player/saver processes.
Rendering never waits for a model. Missing or malformed cached text falls back to
built-in captions; failed generation preserves an existing set. `lk saver text reset`
returns new sessions to built-in captions. Setup requires no new AI provider.

## Fabric PIN curtain

For synchronized Flight Deck curtains, use `lk lock` for settings and `lk lk` to
activate. See [Fabric PIN curtain](CURTAIN.md) for setup, browser controls and
offline behavior. The ordinary saver retains its immediate dismissal keys.

## Saved sets

Open `lk saver` and press **s** for Saved sets. Use Space in the main picker to
select the animations you want, then **s → n** to name and save that selection.
The sets screen lists each set and its members: **l** loads a set, **k** chooses
one for the desktop PIN curtain, and **d** deletes one after confirmation.
Saving an existing name asks before replacing it. Loading a set selects Cycle;
`lk sv` then runs that saved selection. Edit its members with Space and save under
the same name to update it, or a different name to make another set.

Two editable starting sets are provided: **Cinematics** (Flight Deck, Number
Station, Prism Grid, Deep Space Relay, Orbit) and **Cute** (Neon Reef, Paper
Lanterns, Moon Jelly, Firefly Garden, Tide Pools). Existing enabled animations,
colors and display settings are preserved until you choose a set.

```sh
lk saver sets
lk sv --set Cinematics
lk saver --set Cute --save
lk saver --save-set 'My selection'
lk saver --curtain-set Cinematics
lk saver --curtain-set default
lk saver --delete-set 'My selection'
```

Sets contain animation choices; palette, interval and display options remain
independent. Settings live in this device's `~/.config/look/saver.json`. The
saver and desktop PIN curtain can use different sets. Changes apply on their
next launch; they do not alter an active curtain or the browser curtain, and do
not synchronize preferences to other devices. The default curtain remains Flight
Deck with the Bridge palette until a curtain set is explicitly selected.
