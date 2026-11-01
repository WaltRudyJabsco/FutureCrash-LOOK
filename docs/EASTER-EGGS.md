# A local transmission

`lk force` plays Simon Jansen’s Star Wars ASCIIMATION in the terminal.
It is intentionally absent from the ordinary command catalog.

```sh
lk force
lk force --fetch   # prepare/verify the offline copy without playing
lk force --status
lk force --about
```

Space pauses; Left/Right seeks ten seconds; Home or R restarts; Q or Esc exits.
Playback pauses while the terminal is smaller than 69 columns × 18 rows.
The player restores terminal input settings when it exits.

The first launch downloads a checksum-pinned text snapshot over HTTPS. Later
launches play entirely offline from `~/.cache/look/force/starwars.txt.gz`.
Each endpoint can keep its own copy: this snapshot is 73,013 compressed bytes,
contains 3,421 encoded frames, and runs for about 17 minutes 54 seconds.
The fan animation is unfinished; it is not the full feature film.

The repository contains the player, not the third-party animation data.
Original art: [Simon Jansen](https://www.asciimation.co.nz/).
Timing/format: [the author’s FAQ](https://www.asciimation.co.nz/asciimation/ascii_faq.html).
The pinned snapshot comes from
[jimmckeeth/blinkenlights](https://github.com/jimmckeeth/blinkenlights/tree/38a49ac6d4c9969168bf060fef33c67234d65e2f).
`lk force --about` records the exact source; `--status` reports its SHA-256.

The classic Telnet version sent timed text frames and cursor-control sequences
over a terminal connection. LOOK renders the same kind of frame data locally;
it does not open a Telnet server or require a permanently running movie service.
