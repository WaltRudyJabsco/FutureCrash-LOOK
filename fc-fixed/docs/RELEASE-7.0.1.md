# Future Crash + LOOK 7.0.1 — AUTHORITY THAT ACTS

## Mental model

A small interactive demo validates the authority architecture: ordinary user intent should execute at POWER, host policy—not model prose—decides when a command is hazardous, and receipts describe what actually happened.

```text
CONSERVATIVE  observe starting workspace / explicit grants
WORKSPACE     ordinary personal-file work through typed/journaled tools
POWER         normal current-user computer operation; hazardous commands confirm
UNSAFE        unrestricted shell authority within the OS user account
```

## POWER recalibration

POWER now auto-runs ordinary current-user commands rather than prompting for everything outside a tiny inspection whitelist. A deterministic host-side classifier retains native confirmation for commands with destructive/system blast radius, shell composition/redirection, selected dangerous git/package operations, privilege escalation, process killing, disk/network/system administration, and similar operations.

The model does not decide this classification.

## Interactive command truth

Explicit terminal/TUI requests attach to the real TTY. If a launched interactive program is later interrupted with Ctrl-C / exit 130, the receipt records `launched; terminal session interrupted by user` and is typed as an interrupted successful launch rather than a failure to execute.

## Retry authority

Fresh operator requests such as `run it again` or `try it now` deterministically retry the previous command. Earlier failures are evidence, not vetoes. A running LO session also reloads persistent access settings between turns, so changing POWER/UNSAFE through `lk settings` takes effect without restarting LO.

## Receipt continuity

The latest command attempt is retained as an actionable referent and exact host receipt. Subsequent questions about what happened are grounded in that receipt instead of speculative explanations.
