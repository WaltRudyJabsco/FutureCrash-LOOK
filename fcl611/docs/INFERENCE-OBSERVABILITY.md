# Shared Inference Discovery + Observability

LOOK 4.33.10 makes LOOK the authority for Ollama endpoint/model selection and exposes truthful JSONL inference events for independent clients such as Signal Window and Future Crash.

## Discovery

```sh
lk ollama endpoint --json
lk model current --json
lk inference --json
```

`lk ollama endpoint --json` returns the resolved endpoint plus the inherited current model. `lk inference --json` additionally probes `/api/ps` and reports reachability/residency. Existing local, saved remote, Tailscale Serve `:11435`, and `OLLAMA_HOST` override behavior is unchanged.

Example:

```json
{"endpoint":"https://3090.example.ts.net:11435","model":"qwen3.8:27b","source":"saved/discovery","host":"3090"}
```

## LO JSONL events

Invoke the normal LO entry point with `--events-json`:

```sh
lo --events-json "summarize this file" -- /path/to/file
```

The machine stream is stdout. Legacy terminal diagnostics are sent to stderr. Event mode is one-shot: it exits after the final response or error, making it suitable for subprocess clients.

Every event contains:

- `event`: stable event name
- `request_id`: per-request identifier
- `seq`: monotonically increasing event sequence
- `elapsed_ms`: monotonic elapsed time from request creation

Events currently emitted when genuinely observable:

- `request_start`
- `endpoint_resolved` — endpoint, host, source
- `model_selected` — selected shared model
- `model_resident` — boolean plus `/api/ps` running models
- `inference_start` — inference round begins
- `first_token` — first streamed thinking/content/tool-call chunk arrived
- `token_progress` — throttled streamed chunk count (not a tokenizer-exact count)
- `inference_retry` — a real compatibility/re-anchor retry occurred
- `inference_cancelled` — the operator/client interrupted an active inference round
- `inference_done` — Ollama final counters/durations when supplied
- `tool_start`
- `tool_done`
- `response` — complete final assistant text in `text`
- `error`
- `request_done` — terminal request status

Example:

```json
{"event":"request_start","request_id":"a81f","seq":1,"elapsed_ms":0}
{"event":"endpoint_resolved","request_id":"a81f","seq":2,"elapsed_ms":2,"endpoint":"https://3090.example.ts.net:11435","host":"3090","source":"saved/discovery"}
{"event":"model_selected","request_id":"a81f","seq":3,"elapsed_ms":8,"model":"qwen3.8:27b"}
{"event":"model_resident","request_id":"a81f","seq":4,"elapsed_ms":9,"model":"qwen3.8:27b","resident":true,"running_models":["qwen3.8:27b"]}
{"event":"inference_start","request_id":"a81f","seq":5,"elapsed_ms":15,"round":1}
{"event":"first_token","request_id":"a81f","seq":6,"elapsed_ms":811,"round":1}
{"event":"inference_done","request_id":"a81f","seq":7,"elapsed_ms":2401,"round":1,"prompt_tokens":920,"output_tokens":88,"load_ms":12,"eval_ms":1530}
{"event":"response","request_id":"a81f","seq":8,"elapsed_ms":2402,"text":"..."}
{"event":"request_done","request_id":"a81f","seq":9,"elapsed_ms":2402,"status":"ok","rounds":1,"tool_calls":0,"prompt_tokens":920,"output_tokens":88,"load_ms":12}
```

## Streaming semantics

LOOK uses Ollama streaming internally (`stream: true`). `first_token` therefore measures the first observable streamed model output rather than completion of a buffered request. `token_progress` is deliberately throttled and reports chunks; final `output_tokens` uses Ollama's `eval_count` when available.

`model_resident:false` is direct `/api/ps` evidence that the selected model was not resident before the request. LOOK does **not** synthesize a `model_loading` event because Ollama does not provide a reliable transition event for that state through this path. After completion, `load_ms` exposes Ollama's reported `load_duration`, which is the useful diagnostic evidence.

## Errors and timeouts

Streaming HTTP operations have a 180-second network/read timeout. Observable inference failures emit `error` followed by `request_done` with `status:"error"`; the process exits nonzero. A one-shot interruption emits `inference_cancelled` followed by `request_done` with `status:"cancelled"` and exits with status 130. Endpoint failure is also reported as an error. Clients should treat `request_done` as terminal and should not infer success merely from dispatch/start events.

## GPU telemetry

No GPU event is promised by this interface yet. LOOK already has human system/GPU inspection, but remote NVIDIA telemetry is infrastructure-specific and is intentionally not coupled into the inference hot path in this release.

## Priority

This release does not add a scheduler. All consumers inherit LOOK's current model by default, which avoids gratuitous model swaps. A future role/priority field can be added without changing endpoint/model discovery or the event envelope.

## Integration boundary

Signal Window should depend only on the commands/event contract above. It should not reproduce LOOK's Ollama/Tailscale discovery logic.

Relevant implementation: `look/lk` (`_ollama_base`, `_active_ollama_model`, `_InferenceEvents`, `_ollama_stream_chat`, `ollama_chat`).
