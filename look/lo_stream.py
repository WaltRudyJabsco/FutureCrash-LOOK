"""Assemble one LO inference response independently of transport and terminal UI.

Fabric and direct Ollama supply the same normalized event stream. Terminal
lifecycle and error/cancellation handling remain with the caller so a failed
stream cannot bypass its cleanup or become a successful response.
"""

TOKEN_PROGRESS_CHUNKS = 16


def collect_response(stream, *, round_number, on_first_token, on_thinking, events=None):
    """Return (assistant message, last completion event), propagating failures.

    Progress measures text-bearing chunks, not tokenizer counts. Tool calls
    count as first-token activity but do not advance that text progress counter.
    Only the provider's completion event supplies inference accounting.
    """
    message = {"role": "assistant", "content": "", "thinking": "", "tool_calls": []}
    first_event = True
    final_event = {}
    progress_chunks = 0

    for event in stream:
        fragment = event.get("message", {}) or {}
        thought = str(fragment.get("thinking") or "")
        content = str(fragment.get("content") or "")
        calls = fragment.get("tool_calls") or []
        if first_event and (thought or content or calls):
            on_first_token()
            first_event = False
            if events:
                events.emit("first_token", round=round_number)
        if events and (thought or content):
            progress_chunks += 1
            if progress_chunks % TOKEN_PROGRESS_CHUNKS == 0:
                events.emit("token_progress", chunks=progress_chunks, round=round_number)
        if thought:
            message["thinking"] += thought
            on_thinking(thought)
        if content:
            message["content"] += content
        if calls:
            message["tool_calls"].extend(calls)
        if event.get("done"):
            final_event = event

    return message, final_event
