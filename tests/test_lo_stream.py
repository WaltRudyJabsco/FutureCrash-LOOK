"""Behavior contracts shared by Fabric and direct-Ollama inference streams."""
from pathlib import Path
import importlib.machinery
import importlib.util
import sys
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "look"))
import lo_stream


class Events:
    def __init__(self):
        self.rows = []

    def emit(self, name, **fields):
        self.rows.append((name, fields))


def collect(stream, events=None):
    first = []
    thoughts = []
    result = lo_stream.collect_response(
        iter(stream), round_number=3, on_first_token=lambda: first.append(True),
        on_thinking=thoughts.append, events=events,
    )
    return result, first, thoughts


def test_mixed_fragments_preserve_text_thinking_calls_and_completion_accounting():
    calls = [{"function": {"name": "weather", "arguments": {"location": "Portland"}}}]
    done = {"done": True, "eval_count": 7, "load_duration": 1000,
            "message": {"content": "world"}}
    events = Events()
    (message, final), first, thoughts = collect([
        {}, {"message": None},
        {"message": {"thinking": "Let "}},
        {"message": {"thinking": "me think", "content": "Hello "}},
        {"message": {"tool_calls": calls}}, done,
    ], events)
    assert message == {"role": "assistant", "content": "Hello world",
                       "thinking": "Let me think", "tool_calls": calls}
    assert final is done
    assert first == [True]
    assert thoughts == ["Let ", "me think"]
    assert events.rows == [("first_token", {"round": 3})]


def test_tool_only_response_stops_waiting_without_reporting_text_progress():
    calls = [{"function": {"name": "open_path"}}]
    events = Events()
    (message, _), first, thoughts = collect(
        [{"message": {"tool_calls": calls}}] * 32, events,
    )
    assert message["tool_calls"] == calls * 32
    assert first == [True] and thoughts == []
    assert events.rows == [("first_token", {"round": 3})]


def test_progress_counts_text_chunks_once_even_with_both_thinking_and_content():
    events = Events()
    fragments = []
    for _ in range(32):
        fragments.extend([{}, {"message": {"tool_calls": [{}]}},
                          {"message": {"thinking": "t", "content": "c"}}])
    (message, _), _, _ = collect(fragments, events)
    assert message["content"] == "c" * 32
    assert events.rows == [
        ("first_token", {"round": 3}),
        ("token_progress", {"chunks": 16, "round": 3}),
        ("token_progress", {"chunks": 32, "round": 3}),
    ]


@pytest.mark.parametrize("stream", [[], [{}, {"done": True}]])
def test_empty_response_does_not_invent_first_token_activity(stream):
    events = Events()
    (message, _), first, thoughts = collect(stream, events)
    assert message == {"role": "assistant", "content": "", "thinking": "", "tool_calls": []}
    assert first == [] and thoughts == [] and events.rows == []


def test_last_completion_event_is_used_without_stopping_fragment_collection():
    first_done = {"done": True, "eval_count": 1}
    last_done = {"done": True, "eval_count": 2}
    (message, final), _, _ = collect([
        first_done, {"message": {"content": "after"}}, last_done,
    ])
    assert final is last_done and message["content"] == "after"


def test_missing_completion_does_not_invent_accounting():
    (message, final), first, _ = collect([{"message": {"content": "partial"}}])
    assert message["content"] == "partial" and final == {} and first == [True]


@pytest.mark.parametrize("error", [RuntimeError("transport disconnected"), KeyboardInterrupt()])
def test_transport_failure_and_cancellation_propagate_instead_of_returning_partial_success(error):
    def stream():
        yield {"message": {"content": "partial"}}
        raise error

    with pytest.raises(type(error)) as caught:
        collect(stream(), Events())
    assert caught.value is error


def test_first_activity_callback_precedes_event_and_thinking_display():
    order = []

    class OrderedEvents:
        def emit(self, name, **fields):
            order.append(name)

    lo_stream.collect_response(
        [{"message": {"thinking": "thought"}}], round_number=1,
        on_first_token=lambda: order.append("stop waiting"),
        on_thinking=lambda text: order.append(text), events=OrderedEvents(),
    )
    assert order == ["stop waiting", "first_token", "thought"]


def test_display_failure_is_not_swallowed():
    error = OSError("terminal closed")

    def broken_display(text):
        raise error

    with pytest.raises(OSError) as caught:
        lo_stream.collect_response(
            [{"message": {"thinking": "thought"}}], round_number=1,
            on_first_token=lambda: None, on_thinking=broken_display,
        )
    assert caught.value is error


def test_installed_stream_module_is_importable_without_checkout(tmp_path):
    import shutil
    import subprocess

    installed = tmp_path / "installed"
    installed.mkdir()
    shutil.copy2(ROOT / "look/lo_stream.py", installed / "lo_stream.py")
    result = subprocess.run(
        [sys.executable, "-I", "-c",
         "import sys; sys.path.insert(0, sys.argv[1]); import lo_stream; "
         "print(lo_stream.collect_response([], round_number=1, "
         "on_first_token=lambda: None, on_thinking=lambda text: None)[0]['role'])",
         str(installed)], cwd=tmp_path, text=True, capture_output=True,
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "assistant"


@pytest.fixture
def chat(monkeypatch):
    """Keep the real conversation loop; isolate host storage, UI, and providers."""
    loader = importlib.machinery.SourceFileLoader("look_lk_stream_audit", str(ROOT / "look/lk"))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    lk = importlib.util.module_from_spec(spec)
    monkeypatch.setitem(sys.modules, loader.name, lk)
    loader.exec_module(lk)
    monkeypatch.delenv("OLLAMA_HOST", raising=False)

    for name in ("_load_memory", "_load_brain_state", "_load_ai_pool"):
        monkeypatch.setattr(lk, name, lambda: {})
    for name in ("_brain_context", "_recent_context", "_world_context"):
        monkeypatch.setattr(lk, name, lambda: "")
    monkeypatch.setattr(lk, "_memory_context", lambda *args: "")
    monkeypatch.setattr(lk, "_live_state_context", lambda *args: "")
    monkeypatch.setattr(lk, "_lo_latest_command_action", lambda: None)
    route = SimpleNamespace(primary="general", families=["general"], confidence=1.0,
                            margin=1.0, source="test", allowed_tools=[])
    monkeypatch.setattr(lk, "_lo_cognition_route", lambda *args, **kwargs: route)
    monkeypatch.setattr(lk, "_lo_goal", lambda *args: None)
    monkeypatch.setattr(lk, "_lo_tools_for_route", lambda *args: [])
    monkeypatch.setattr(lk, "_lo_budget_for", lambda *args: (
        "test", {"context": 4096, "output": 512, "tool_rounds": 3}))
    monkeypatch.setattr(lk, "_queue_skill_feedback", lambda *args: False)
    monkeypatch.setattr(lk, "_queue_memory_exchange", lambda *args, **kwargs: True)
    monkeypatch.setattr(lk, "_save_recent_exchange", lambda *args: None)
    monkeypatch.setattr(lk, "_ensure_ollama_server", lambda *args, **kwargs: [])
    monkeypatch.setattr(lk, "_ollama_tags", lambda *args: [{"name": "test-model"}])
    monkeypatch.setattr(lk, "_preferred_model_for_base", lambda *args, **kwargs: "test-model")
    monkeypatch.setattr(lk, "_ollama_capabilities", lambda *args: ["thinking", "tools"])
    stats, foreground, waiting, thoughts = [], [], [], []
    monkeypatch.setattr(lk, "_record_ai_stats", stats.append)
    monkeypatch.setattr(lk, "_ai_foreground", lambda active, *args: foreground.append(active))

    class Waiting:
        def __init__(self, label):
            self.finished = 0
            waiting.append(self)

        def start(self):
            return self

        def finish(self):
            self.finished += 1

    class Thinking:
        def __init__(self, mode):
            pass

        def feed(self, text):
            thoughts.append(text)

        def finish(self):
            pass

    monkeypatch.setattr(lk, "_ActivityHandle", Waiting)
    monkeypatch.setattr(lk, "_RollingThinking", Thinking)
    return lk, stats, foreground, waiting, thoughts


@pytest.mark.parametrize("transport", ["fabric", "ollama"])
@pytest.mark.parametrize("outcome", ["ok", "error", "cancelled"])
def test_real_chat_loop_preserves_transport_events_accounting_and_cleanup(
        chat, tmp_path, monkeypatch, transport, outcome):
    lk, stats, foreground, waiting, thoughts = chat
    requests = []

    def stream(*args, **kwargs):
        requests.append((args, kwargs))
        yield {"message": {"thinking": "Reasoning.", "content": "Rainbows "}}
        if outcome == "error":
            raise RuntimeError("stream failed")
        if outcome == "cancelled":
            raise KeyboardInterrupt()
        yield {"message": {"content": "form through refraction."}, "done": True,
               "prompt_eval_count": 12, "eval_count": 8,
               "prompt_eval_duration": 2000000, "eval_duration": 3000000,
               "load_duration": 4000000}

    def unexpected(*args, **kwargs):
        raise AssertionError("wrong transport selected")

    monkeypatch.setattr(lk, "_fabric_stream_chat", stream if transport == "fabric" else unexpected)
    monkeypatch.setattr(lk, "_ollama_stream_chat", stream if transport == "ollama" else unexpected)
    events = Events()
    result = lk.ollama_chat(
        initial_prompt="Explain why rainbows form.", access_profile="conservative",
        workspace_override=tmp_path, one_shot=True, events=events,
        host_override=None if transport == "fabric" else "http://test-ollama",
    )
    assert result == {"ok": 0, "error": 1, "cancelled": 130}[outcome]
    assert len(requests) == 1 and waiting[0].finished == 2
    assert thoughts == ["Reasoning."] and foreground[-1] is False
    names = [name for name, fields in events.rows]
    assert names.count("first_token") == 1 and names.count("inference_start") == 1
    done = [fields for name, fields in events.rows if name == "request_done"][-1]
    assert done["status"] == outcome
    if outcome == "ok":
        response = [fields["text"] for name, fields in events.rows if name == "response"]
        assert response == ["Rainbows form through refraction."]
        assert done["prompt_tokens"] == 12 and done["output_tokens"] == 8 and done["load_ms"] == 4
        assert stats[0]["prompt_s"] == .002 and stats[0]["eval_s"] == .003
        assert stats[0]["load_s"] == .004
    else:
        assert "response" not in names and "inference_done" not in names and stats == []


@pytest.mark.parametrize("transport", ["fabric", "ollama"])
def test_real_chat_tool_continuation_has_fresh_response_and_accumulates_round_metrics(
        chat, tmp_path, monkeypatch, transport):
    lk, stats, _, waiting, _ = chat
    requests = []

    def stream(*args, **kwargs):
        payload = args[0] if transport == "fabric" else args[1]
        requests.append((list(payload["messages"]), kwargs.get("route")))
        message = ({"tool_calls": [{"function": {"name": "wikipedia",
                                                 "arguments": {"query": "Rainbow"}}}]}
                   if len(requests) == 1 else {"content": "Rainbows involve refraction."})
        yield {"message": message, "done": True, "prompt_eval_count": 10,
               "eval_count": 5, "load_duration": 1000000}

    monkeypatch.setattr(lk, "_fabric_stream_chat", stream)
    monkeypatch.setattr(lk, "_ollama_stream_chat", stream)
    monkeypatch.setattr(lk, "_wikipedia_lookup", lambda query: "Trusted rainbow background.")
    events = Events()
    assert lk.ollama_chat(
        initial_prompt="Explain why rainbows form.", access_profile="conservative",
        workspace_override=tmp_path, one_shot=True, events=events,
        host_override=None if transport == "fabric" else "http://test-ollama",
    ) == 0
    assert len(requests) == 2 and all(handle.finished == 2 for handle in waiting)
    assert {"role": "tool", "tool_name": "wikipedia", "content": "Trusted rainbow background."} in requests[1][0]
    if transport == "fabric":
        assert requests[0][1] is requests[1][1]
    responses = [fields["text"] for name, fields in events.rows if name == "response"]
    assert responses == ["Rainbows involve refraction."]
    done = [fields for name, fields in events.rows if name == "request_done"][-1]
    assert done["rounds"] == 2 and done["tool_calls"] == 1
    assert done["prompt_tokens"] == 20 and done["output_tokens"] == 10 and done["load_ms"] == 2
    assert stats[0]["rounds"] == 2 and stats[0]["tool_calls"] == 1
