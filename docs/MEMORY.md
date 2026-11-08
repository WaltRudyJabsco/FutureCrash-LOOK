# Conversational memory

LO, Signal and Albert use the same background memory pipeline on their serving host. An exchange is queued durably, extracted into a candidate, and reconciled against shared user records. A correction updates the existing record rather than adding two competing preferences. Records retain user evidence, originating interface, revision and source node. Existing durable local memories migrate with an explicit legacy provenance label.

This is learning through stored context, not model-weight training. It is asynchronous: an assistant acknowledgement is not proof that a background write completed. `lk memory` shows extraction outcomes, shared-write/sync status, pending jobs and retained failures. `lk memory shared` shows shared records; `lk memory sync` requests convergence now. Idle background workers retry peer synchronization every five minutes, including after a peer reconnects.

Malformed responses, deliberate empty extractions, filtered content and errors are distinguished. A failed job retries up to three times, then remains as a private `.failed` file in the memory queue instead of blocking newer work. `lk memory retry` requeues retained failures. `lk memory forget TEXT` removes matching local and shared user facts; replicated deletion markers prevent an old peer from bringing them back. `lk memory clear` clears local LO user memory and shared user facts. These commands do not erase all historical conversation logs or backups.

Recent shared corrections receive a small reserved context budget so a paraphrase need not share exact words with the stored preference. Lexically relevant records extend that budget. This is bounded retrieval, not a guarantee of semantic recall over an unlimited archive. Preferences remain context, never tool permissions or executable policy. Focused delivery workflows preserve that context. For general conversation with shared preferences, a compact response pass uses the configured primary model rather than treating a short question as suitable for the smallest reflex model. If the model indicates tools are needed, the normal tool loop remains available.

The final displayed answer is the answer recorded for memory. Tool completion records identify the tool that completed; they do not imply that an entire compound task succeeded. Learned skills remain stored beyond 24 entries; the prompt selects at most 24 by confidence and recency.

## Verification

Run deterministic regression checks with:

```sh
PYTHONPATH=look:core:. python3 -m pytest tests/test_memory_learning.py tests/test_fabric_memory.py tests/test_tool_workflow.py tests/test_lo_engine.py tests/test_lo_stream.py
```

With a local Fabric running, run `python3 tools/check_memory_learning.py`. The live check uses disposable memory/session files, actual model inference, the terminal core and Signal/Albert entry points. It captures a synthetic preference through LO, corrects it through Signal, checks compression, and asks each interface to retrieve the corrected value from reopened replicas with no local conversation history. Effect tools are blocked; nothing prints. `--model NAME` is available for diagnosis, but the normal-routing run is the deployment acceptance check.

This proves one correction path, not general reasoning reliability. Older models can still mishandle unrelated document/tool requests; those failures should be evaluated separately rather than counted as memory successes.
