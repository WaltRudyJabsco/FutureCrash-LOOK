# 1.1.3 — Memory sanitation

- Strip paired and orphaned Qwen thinking output before persistence.
- Candidate worker fails closed unless output is exactly `NONE` or `NN|text`.
- Reject common model-meta/reasoning patterns.
- Invalid summary rewrites retain the previous clean summary.
- Existing contaminated candidates are pruned automatically on memory load.
- Adds `lk memory prune` and `lk memory clear-summary`.
- Candidate limits, importance, decay, and skills architecture are unchanged.
