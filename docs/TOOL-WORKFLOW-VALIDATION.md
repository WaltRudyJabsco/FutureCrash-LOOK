# Content delivery workflow checks

LO, Signal and Albert use the same inference/tool execution core. Content-delivery
turns use a focused contract, the applicable tool-family union, current resource
and access context, and the current transaction's tool receipts. Referenced prior
conversation is source material, not execution policy.

An explicit print/save request authorizes that requested effect. Preparation alone
is not completion. A successful Notes receipt satisfies a Notes action, rather
than requiring an unrelated filesystem mutation. One bounded recovery turn can
correct unnecessary clarification; uncertain print submissions are never retried.

When a print call omits its destination, the host can resolve one exact discovered
printer label in the user's request. Ambiguous choices stop. Preview and negative
requests do not send paper. Generated placeholders and inconsistent weekday/date
pairs are rejected before delivery.

## Live inference audit

From the repository root, with an Ollama-compatible service available:

```sh
PYTHONPATH=look:core:. python tools/check_tool_workflow.py --model MODEL
```

Use `--endpoint` to select another compatible chat endpoint. The audit exercises
the actual shared engine and live inference, including a live weather lookup.
Printer submission and Notes storage are replaced with fixture endpoints: no
paper is used and no notes are saved. It asserts exactly one completed effect and
checks essential supplied content, unfinished placeholders and date consistency.
It covers a supplied shopping list, a supplied-text summary saved to Notes, and a
retrieved forecast printed as Markdown. This verifies orchestration, not physical
printer delivery or the quality of every possible model answer.

Regression coverage additionally checks scoped compound routes, retained resource
context, stale confirmation history, printer ambiguity, preview-only behavior,
receipt completion, pending task state and duplicate-print prevention.

## Terminal conversation audit

```sh
PYTHONPATH=look:core:. python tools/check_terminal_workflow.py
```

This runs the real multi-turn POWER terminal loop with normal Fabric routing,
model selection, temperature and thinking settings. It requests an illustrated
forecast, a Renoir artwork, then “how about printing a three day forcast.”
Only printer discovery/submission are fixtures; no real paper is sent. Unexpected
shell actions are blocked. It asserts three separate requested effects and the
illustration on the first receipt. This supplements deterministic model audits;
passing a forced-model single-turn test alone is not sufficient validation.

Conversational printing invitations normalize before task routing. A new request
replaces the prior task. Unique near-exact printer-name replies can use the live
catalog, but ambiguous names are not guessed. “It didn't print” resumes only a
still-unsubmitted request; state is cleared before an actual submission. Failed
completion reports replace unsupported success prose instead of prepending a
warning to the same false claim.
