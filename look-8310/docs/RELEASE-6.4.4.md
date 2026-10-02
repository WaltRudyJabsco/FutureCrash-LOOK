# 6.4.4 · Shall We Play

LOOK Games graduates from two hidden Easter eggs into one small terminal game family.

- `lk games` opens the WOPR recreation channel.
- `lk games ttt [0p|1p|2p]`
- `lk games checkers [0p|1p|2p]`
- `lk games chess [0p|1p|2p]`
- `lk games backgammon [0p|1p|2p]`
- `lk games gtnw` keeps Global Thermonuclear War as a deliberately 0-player simulation.
- `lk ttt` and `lk gtnw` remain aliases.

The board games share the same terminal shell and common controls. `0p` is computer-versus-computer attract mode, `1p` is human-versus-computer, and `2p` is local hot-seat play. `s` stops, `r` restarts, `h` opens terse help, and `q`/Esc exits. In `0p`, Space pauses/resumes.

The engines are deliberately lightweight and dependency-free. Tic-tac-toe uses perfect minimax; checkers uses mandatory captures plus shallow alpha-beta; chess uses legal move generation and shallow alpha-beta; backgammon uses normal hitting, bar entry, doubles and bearing off with a compact heuristic. Chess intentionally omits castling and en passant to keep the Easter egg auditable and small.
