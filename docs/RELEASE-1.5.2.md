# 1.5.2 — Future Crash artifact hardening

Versions:
- Future Crash + LOOK 1.5.2
- LOOK 3.8.0
- Future Crash 1.0.2

- Fixes the Future Crash runtime/header version constant.
- Fortunes and ambient observations reject obvious prompt-paraphrase/reasoning leakage.
- If a short model response contains reasoning but no usable final artifact, Future Crash falls back to its local fortune/observation seed.
- Conversational Ask/Work output still uses the normal final-answer extractor.
