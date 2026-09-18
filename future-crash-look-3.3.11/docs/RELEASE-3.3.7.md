# 3.3.8 — Cheap Failure / Hard Turn Boundary

- Fixes the missing session turn-counter increment introduced with resource recency.
- Every prompt starts fresh retry/evidence/action state; ResourceRefs and conversation remain available.
- Known compatible resources outrank filesystem search; explicit constraints such as `that HTML file` outrank pure recency.
- Document continuation is bounded to one recovery attempt per turn.
- LO's planner now follows bounded initiative: cheap deterministic work first; ask for one useful clue when uncertainty stops decreasing.
- Typed browser actions remain typed host actions.

Design rule: when uncertainty stops decreasing cheaply, return control to the human.
