# Future Crash + LOOK 7.0.0 — WORLD STATE

## Mental model

Models may sleep; goals stay alive. Language is an interface and reasoning medium, not the system of record. Host state, actions, failures, and task progress are represented as typed persistent data.

```text
operator/events -> cognition route -> persistent goal/task graph
                -> structural preflight -> primitive/tool
                -> typed receipt -> world state -> verify/close/wake
```

## New persistent world state

`~/.local/share/look/world_state.json` is a compact bounded store containing:

- active and recent goal/task graphs
- typed action receipts with exact failure messages
- failure classification (`host_bug`, `permission`, `missing_resource`, `transient_or_timeout`, `policy_guard`, `action_failure`)
- execution policy (`normal` vs `deliberate`, preflight, verification requirement)
- bounded events and wake reasons

The existing `brain_state.json` still owns human-input slots and working clarification state. World state owns machine/action truth. The two are injected together into LO cognition.

## Tool boundary

The existing `_tool_transaction` is now the architectural choke point:

1. derive structural execution policy
2. persist action preflight
3. execute the primitive
4. normalize its result into typed truth
5. write the forensic receipt journal
6. write the persistent world-state receipt
7. let goal verification close or retain the task

This keeps ordinary reads fast while giving mutations, shell commands, media, scheduling, browser/display effects, and destructive actions a deliberate/verified path.

## Failure intelligence

A failure is no longer merely assistant prose. The exact tool receipt is persistent. `what was the tool error?` is answered directly from host state. Previous failure never suppresses a later explicit operator retry.

The `asciiquarium` regression also restores `_looks_like_shell_file_discovery`, which was called by `run_command` but absent from the installed code. The guard blocks shell-based file discovery while allowing unrelated commands such as `asciiquarium`.

Explicit “in the terminal” requests now set the command transaction to interactive mode and attach the child process to the real TTY. Non-interactive commands retain bounded captured stdout/stderr.

## Observability

```bash
lk world
lk brain
lk receipts
```

`lk world` shows the active typed goal, recent receipts/failures, and bounded world events.
