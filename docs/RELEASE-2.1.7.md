# Future Crash + LOOK 2.1.7 — Input polish + AI performance telemetry

Versions:

- Future Crash + LOOK: 2.1.7
- LOOK: 4.1.7
- Future Crash: 1.1.8

## Filer

- `Tab` and `Shift-Tab` both toggle the highlighted mark.
- `←` goes to the parent directory wherever parent navigation is available.
- `→` follows the same inward/open behavior as Enter.
- Footer wording distinguishes `B clipboard`, `C Copy To`, and `M Move To`.

## Waiting feedback

LOOK's four-frame activity indicator now appears for operations where the user is genuinely waiting: first model response, blocking filesystem mutations, explicit command execution, and global file catalog scans. Background memory/skill work remains non-blocking and therefore reports receipts rather than spinners.

## AI performance

`lk ai stats` stores a rolling 100-request telemetry window without prompt/response content.

Per task:

- wall time
- inference rounds
- tool calls
- prompt token count and prompt-eval time/rate
- generated token count and generation time/rate
- model load duration

Live Ollama status adds model VRAM allocation and context length from `/api/ps`. A local NVIDIA host also adds `nvidia-smi` memory/utilization/temperature detail. Remote hosts are never mislabeled with the local machine's GPU statistics.
