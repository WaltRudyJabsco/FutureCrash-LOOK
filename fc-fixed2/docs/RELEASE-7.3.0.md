# 7.3.0 — LIVE STATE

Future Crash + LOOK now distinguishes durable history from present-tense state. `core/live_state.py` maintains a bounded pool of typed live objects with provenance, freshness, TTL and retirement. Host receipts update this pool automatically; cheap inspectors reconcile objects where authoritative state is available. JEV resolves actions against live objects rather than replaying receipt history, and general cognition receives only a relevant state slice.

This release establishes the spinning-plates contract: hot environmental facts stay fresh and disposable; durable skills, procedures and receipts remain separate.
