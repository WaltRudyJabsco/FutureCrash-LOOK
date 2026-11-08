# Shared task understanding

LO, Signal and Albert use the same semantic task interpreter and execution loop.
The interpreter reads the user's current wording, bounded conversation context,
and the available tool catalog. It produces a desired outcome, a set of useful
capabilities, and explicit completion obligations. The configured primary model
handles interpretation and execution; exact commands still use their direct paths.

This is separate from tool arguments and results. A planner cannot invent a new
tool, broaden the access profile, certify success, or turn a malformed answer
into an action. Invalid interpretation falls back to a conversation without tools.
The executor uses actual source results and existing workspace/paper limits.

Examples include composing a reply, putting that reply on paper, saving a summary
as a note, and changing direction without repeating the preceding action. A task
that requires delivery remains pending when only retrieval succeeded. Conversational
phrasing can authorize bounded print/Notes actions through the validated task;
callers without that host context retain their existing explicit-request checks.

## Session state and evidence

`look/task_brain.py` stores the current interpretation, original user request,
answer, attempted tool names, and successful tool receipts in the existing private
browser session store (terminal context lives for the chat process). Sessions remain separate; shared code does not mean shared
implicit authorization. Pending context expires after 30 minutes. Durable preferences
continue through the Fabric memory system described in [Memory](MEMORY.md).

New requests replace stale tasks; continuations retain relevant context. Superseded
actions are removed from the exposed tools. Identical effect calls are blocked
within a turn. An uncertain print submission is not automatically repeated on a
continuation. Queue acceptance still does not prove physical printing.

`task_interpreted` events expose the plan for diagnosis. `goal_verified` compares
its completion obligations with host receipts. Existing world-state and memory
records receive the resulting goals/actions; this change does not train model
weights or expand Jev's inference capabilities.

## Validation

Run `tools/check_task_brain.py` with a working Fabric. It exercises the real LO,
Signal, and Albert entry points with the configured model and isolated state.
Print transport is intercepted (no paper); Notes writes use a disposable fixture;
file writes use the actual filesystem tool in a temporary workspace. Assertions
check content, tool selection, effect counts, and persisted file contents.

Interpretation adds one inference call. It can still misunderstand a request;
the test harness provides repeatable evidence for specific interactions, not a
claim of universal comprehension. Oversized context is bounded, and missing tool
capabilities remain explicit limitations.
