# Sibling panes and Pacific Tech

In LOOK's file browser, Escape leaves FILTER without opening a file. From BROWSE,
press **W** (Shift-W) to open a sibling shell in the directory currently viewed.
The original LOOK stays open. The new shell can run `l`, `lk`, `lkn`, `lk player`
or any other command. W remains search text in FILTER and is not an editor shortcut.
Remote Fabric directories are not local shell working directories.

With the shared Kitty profile (`./install.sh --kitty`, then fully quit and restart Kitty once):

- Option/Alt-Shift-W cycles pane focus; two panes toggle back and forth.
- Ctrl-Shift-W closes the focused pane; Command-W also works on Mac.
- Ctrl-Shift-Enter opens a shell split from any program, in its working directory.
- Inactive panes are gently dimmed. Each pane is an independent terminal process;
  closing one does not close its sibling. Closing the whole OS window closes its panes.
- Escape keeps the active application's meaning. Exiting LOOK in a sibling shell
  returns to that shell; `exit` or the terminal close shortcut closes the pane.

After W successfully opens a pane, LOOK keeps the focus/close shortcuts in its
footer in both BROWSE and FILTER. The opening notice includes the same reminder.
On Mac it says Option-Shift-W; on other Kitty platforms it says Alt-Shift-W.
This reminder belongs to the original LOOK session; the sibling remains a normal
independent shell.

Opening or closing a pane wakes LOOK on the terminal's resize signal. The surviving
browser reflows its grid and footer at the new width immediately, preserving its
filter/marks and keeping the current page within the rebuilt list.

The W helper also supports existing tmux sessions. Use tmux's configured pane
focus/close shortcuts there (defaults: Ctrl-B then O, and shell `exit`).
Other terminals continue to run LOOK normally; W explains that splits require
Kitty or tmux. No terminal emulator or multiplexer is installed on demand.

Kitty control is limited to `launch` and `goto-layout` with the `look-panes`
action password. This is an action scope, not a private credential. No socket
listener, screen-reading, input-injection or general remote-control permission
is added. Personal `kitty-local.conf` overrides remain last.

## After-hours laboratory

Original ASCII tributes to Real Genius, independent of media playback:

    lk genius           # laboratory doors: 1 popcorn, 2 Lazlo, 3 Kent, 4 laser
    lk genius --tour    # rotate through all four scenes every 14 seconds
    lk popcorn          # laser-powered home improvement
    lk lazlo            # closet and fictional sweepstakes printer
    lk kent             # car assembly inside a dormitory
    lk laser            # mirrors and an optical party finder

All five commands support 1-4 to change scene, G to return to the lab, T to toggle
the tour, Space to pause, and Q/Escape to exit. Terminal resizing is handled on
each frame; exiting restores the prior screen and terminal mode. Piped output
prints a static, plain-text scene and finishes. No network, file writes, audio,
actual sweepstakes submissions or changes to the existing player queue occur.

The player also gains **Moon Jelly**, an ambient ASCII aquarium with pulsing
jellyfish bells, trailing tendrils and rising bubbles. It joins Cycle's existing
ten-second rotation in `lk player` and `lk mp`; pause freezes its animation.
