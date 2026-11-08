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

## Conversation and proposals

Conversation remains available to the executor on every turn, including numbered
selections and questions about previously retrieved results. Dialogue is context,
not proof that an action occurred or a source of new permission rules.

Clear requests execute without ritual confirmation. When materially different
actions fit, or the assistant suggests an action of its own, the interpreter can
return `propose`: a concrete intended outcome and one focused question. The host
stores this proposal and returns the question **without executing any tools**.
A question about the offer preserves it; approval proceeds, an amendment changes
the scope, and cancellation discards it. The model interprets those replies in
context rather than matching a fixed list of approval phrases. Essential missing
content still gets a specific input question instead of a vague approval prompt.

Offers are bounded to known tools and the current session. Stored proposal context
expires after 30 minutes and never grants permissions outside the current access profile. A completed action
is not an outstanding offer. This remains model-mediated interpretation, so the
system can still misunderstand; it is not a formal authorization proof.

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
Print transport is intercepted (no paper); Notes use their real store in a disposable directory;
file writes use the actual filesystem tool in a temporary workspace. Assertions
check content, tool selection, effect counts, and persisted file contents.
Use `--dialogue` for live Museum discussion, numbered selections, uncertain-action
proposals, questions about offers, amendments, approval, and cancellation across
all three interfaces. These tests intercept writes and use real model inference;
Museum discovery is a real read-only call.

Fabric preserves JSON output mode through the worker to the model. Invalid structured
output gets one bounded repair attempt without effects, then falls back to a
tool-free conversation if still invalid.

Interpretation normally adds one inference call. It can still misunderstand a request;
the test harness provides repeatable evidence for specific interactions, not a
claim of universal comprehension. Oversized context is bounded, and missing tool
capabilities remain explicit limitations.
