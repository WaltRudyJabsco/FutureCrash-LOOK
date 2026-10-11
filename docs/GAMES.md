# Rooftops

`lk games rooftops` opens the existing LOOK Games doorway with Rooftops selected.
The playful `LOGON: JOSHUA` entrance is a WarGames reference, not authentication.
Rooftops is menu item 6; existing game numbers stay the same. `roof`, `roofs`, and
`rooftop` are also accepted after `lk games`.

Choose a mode in the menu, or include it in the command:

| Command | Mode | Jump controls |
| --- | --- | --- |
| `lk games rooftops 0p` | Automatic demonstration | No input required; Space pauses |
| `lk games rooftops 1p` | Solo survival run | Space or Z |
| `lk games rooftops 2p` | Two runners on one keyboard | Z for P1, / for P2 |

The runners share the same course in separate lanes. Jump before a rooftop gap;
you cannot jump again in midair. A missed landing ends that runner's attempt.
The other runner continues, and the longest distance wins. Simultaneous falls
are a draw. This is local play; no networking or separate accounts are needed.

P pauses both lanes. R restarts the same skyline seed, shown in the header, so
you can practice or rematch fairly. H opens help, S stops, and Q/Esc returns to
the game selector. Small terminals pause the simulation until enlarged: at
least 40 columns and 12 rows for one runner, or 19 rows for two.

The game generates an original 92 BPM swing loop locally: bleep bass, light
percussion and a sparse melody. M toggles music, which pauses with the game and
stops on game-over, help or exit. Playback uses its own mpv process at 25% player
volume through the host's current default output; LOOK queues and OS routing
settings are untouched. Missing mpv leaves the game playable with an
unavailable music status. `LOOK_GAMES_MUSIC=0 lk games rooftops 1p` starts muted.

The media-player Rooftops visualizer remains an automatic, silent animation.
