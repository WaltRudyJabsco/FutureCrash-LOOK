# 6.4.6 · FALKEN

LOOK Games presentation and voice polish.

- Chess and checkers now render with alternating terminal-square backgrounds and coordinates on both edges.
- Backgammon now renders a framed board with point numbers, center bar, circular checkers, stacks, dice, and off counts.
- `q`/Esc returns board games to the WOPR menu; `s` stops. GTNW keeps its special simulation behavior.
- Every interactive WOPR entrance performs `LOGON: JOSHUA`; bare `lk games` then still reports `NO GAMES INSTALLED.`
- Sparse offline WOPR speech: macOS `say`/Zarvox; Linux `espeak-ng`, with SoX processing when `play` is available.
- Default workstation dependencies add SoX everywhere and eSpeak NG on Linux.
