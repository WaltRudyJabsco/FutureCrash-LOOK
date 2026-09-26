# Future Crash + LOOK 3.3.9 — Shared Inference Observability

- LOOK is now explicitly consumable as the Ollama endpoint/model authority.
- Added machine-readable endpoint, current-model, and inference-status commands.
- Added one-shot LO JSONL event streaming with request IDs and monotonic elapsed timing.
- Preserved Ollama token streaming and exposed first-token/final Ollama timing counters.
- Added model residency telemetry from Ollama `/api/ps`.
- Added truthful tool start/done events without replacing human terminal receipts.
- Fixed the unbound `turn_document_reanchors` continuation crash in the streaming adapter.
- Kept Signal Window and Future Crash independent of inference discovery internals.
