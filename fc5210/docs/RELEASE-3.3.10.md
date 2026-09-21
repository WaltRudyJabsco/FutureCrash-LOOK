# Future Crash + LOOK 3.3.10 — Inference Cancellation Reliability

- Enforces the documented 180-second timeout on the primary streamed Ollama chat request.
- Machine one-shot cancellation now emits `inference_cancelled` and terminal `request_done` events.
- A cancelled `--events-json` one-shot exits immediately with status 130 instead of falling back to another interactive prompt.
- Preserves the 3.3.9 shared endpoint/model discovery and pure-stdout JSONL contract.
- No renderer, tool-policy, memory, or Future Crash behavior changes.
