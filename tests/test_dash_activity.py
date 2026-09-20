import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("fcl_node", ROOT / "core" / "node.py")
node = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = node
spec.loader.exec_module(node)


def test_dash_activity_colors_are_semantic_not_stream_noise():
    assert node._dash_event_flash({"type":"progress", "phase":"dispatch"}) == "44;97"
    assert node._dash_event_flash({"type":"progress", "phase":"inference"}) == "48;5;214;30"
    assert node._dash_event_flash({"type":"release", "phase":"ok"}) == "42;30"
    assert node._dash_event_flash({"type":"release", "phase":"failed"}) == "41;97"
    assert node._dash_event_flash({"type":"progress", "phase":"stream"}) is None


def test_dash_recent_scope_distinguishes_local_and_remote():
    assert node._dash_event_scope({"node":"m4"}, "m4") == "LOCAL"
    assert node._dash_event_scope({"node":"3090"}, "m4") == "REMOTE"


def test_model_qualification_states_are_explicit():
    t = 1_000_000.0
    assert node._qualification_state({}, current=t)[0] == "untested"
    assert node._qualification_state({"qualification":{"tested_at":t-10,"ok":True}}, current=t)[0] == "qualified"
    assert node._qualification_state({"qualification":{"tested_at":t-node.QUALIFY_RECHECK_SECONDS-1,"ok":True}}, current=t)[0] == "stale"
    assert node._qualification_state({"qualification":{"tested_at":t-10,"ok":False}}, current=t)[0] == "failed"


def test_dash_model_summary_distinguishes_residency_and_qualification():
    t = node.now()
    info = {
        "inference": {
            "preferred_model": "qwen3:8b",
            "resident": ["qwen3:8b", "gemma3:1b"],
            "models": [
                {"name":"qwen3:8b", "resident":True,
                 "qualification":{"tested_at":t-60,"ok":True,"generation_tok_s":62.0}},
                {"name":"gemma3:1b", "resident":True},
            ],
        }
    }
    rendered = node._dash_model(info)
    assert "qwen3:8b" in rendered
    assert "R2" in rendered
    assert "Q 1m" in rendered
    assert "62t/s" in rendered


def _dash_fixture():
    t=node.now()
    local={
        "name":"3090","version":node.VERSION,"pulse":{"number":123},
        "capabilities":{"filesystem":True},"supervisor":{"active":None},
        "inference":{
            "preferred_model":"qwen3.8:27b","resident":["qwen3.8:27b"],
            "models":[{"name":"qwen3.8:27b","resident":True,
                       "qualification":{"tested_at":t-60,"ok":True,"generation_tok_s":56.0},
                       "benchmark":{"tested_at":t-120,"fit":"EXCELLENT","tools":3,"agent":True,"exact":True}}],
        },
    }
    peer={"name":"m3","node_seen_at":t-2,"node":{
        "name":"m3","version":node.VERSION,"pulse":{"number":123},"supervisor":{"active":None},
        "inference":{"preferred_model":"qwen3:8b","resident":["qwen3:8b"],"models":[{"name":"qwen3:8b","resident":True}]},
    }}
    events={"events":[{"seq":i,"ts":t-i,"node":"m3","type":"progress","phase":"inference","detail":"qwen3:8b responding"} for i in range(1,8)]}
    return {
        "nodes":{"self":local,"peers":[peer]},"health":{"ok":True},"jobs":{"jobs":[]},
        "http":{"listeners":{"local":{"requests_completed":12,"active":0,"errors":0}}},
        "services":{"services":{"node":{"state":"running"},"signal":{"state":"running"}}},
        "events":events,
    }


def test_dash_live_renderer_never_pages_medium_height():
    body=node._dash_render(_dash_fixture(),92,height=28,ansi=False)
    assert len(body.splitlines()) <= 28
    assert "RECENT" in body
    assert "[q] quit" in body
    assert "TRUST BASIS" not in body


def test_dash_live_renderer_protects_recent_in_short_window():
    body=node._dash_render(_dash_fixture(),82,height=18,ansi=False)
    assert len(body.splitlines()) <= 18
    assert "RECENT" in body
    assert "responding" in body
    assert "[q] quit" in body


def test_dash_snapshot_without_height_remains_full():
    body=node._dash_render(_dash_fixture(),92,ansi=False)
    assert "TRUST BASIS" in body
    assert "CONTROL PLANE" in body
    assert "SERVICES" in body


def test_dash_model_includes_full_benchmark_evidence_compactly():
    rendered=node._dash_model((_dash_fixture()["nodes"]["self"]))
    assert "B:EXCE" in rendered
    assert "T3/3" in rendered
    assert "A✓" in rendered
    assert "E✓" in rendered
