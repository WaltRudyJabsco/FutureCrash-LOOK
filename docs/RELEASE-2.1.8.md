# Future Crash + LOOK 2.1.8 — Warm model residency

Versions:

- Future Crash + LOOK: 2.1.8
- LOOK: 4.1.8
- Future Crash: 1.1.8

LO now sends `keep_alive=-1` on normal interactive Ollama chat requests.

This targets the measured failure mode where a Qwen 30B task spent more than half its wall time reloading ~19 GB of model weights before doing useful work.

`lk ai stats` classifies tasks as:

- **cold** when cumulative Ollama load duration is at least 1 second
- **warm** otherwise

For remote Ollama hosts, `/api/ps` exposes model residency, not physical GPU capacity. The stats surface now labels these fields correctly as `GPU resident` and `model size`.
