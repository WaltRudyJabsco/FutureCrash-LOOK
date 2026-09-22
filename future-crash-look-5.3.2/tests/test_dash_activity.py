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
    assert "R[q3:8b,g3:1b]" in rendered
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
                       "benchmark":{"tested_at":t-120,"fit":"EXCELLENT","tools":3,"agent":True,"exact":True,
                                    "ttft":0.8,"rate":56.0,"reasoning":3}}],
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


def test_dash_model_includes_purpose_evidence_compactly():
    rendered=node._dash_model((_dash_fixture()["nodes"]["self"]))
    assert "RFX3/3" in rendered
    assert "RSN3/3" in rendered
    assert "T3/3" in rendered
    assert "A✓" in rendered



def test_dash_landscape_uses_width_instead_of_collapsing_to_compact():
    body=node._dash_render(_dash_fixture(),120,height=22,ansi=False)
    assert len(body.splitlines()) <= 22
    assert "NODES / MODELS" in body
    assert "CONTROL ·" in body
    assert "TRUST ·" in body
    assert "SERVICES ·" in body
    assert "RECENT" in body


def test_dash_medium_uses_available_rows_for_telemetry_and_recent():
    body=node._dash_render(_dash_fixture(),92,height=28,ansi=False)
    lines=body.splitlines()
    assert len(lines) >= 24
    assert len(lines) <= 28
    assert "JOBS ·" in body
    assert "SERVICES ·" in body
    assert "TRUST ·" in body
    assert "RECENT" in body


def test_dash_portrait_prefers_full_when_full_content_fits():
    body=node._dash_render(_dash_fixture(),82,height=50,ansi=False)
    assert "TRUST BASIS" in body
    assert "CONTROL PLANE" in body
    assert "SERVICES" in body



def test_dash_live_lines_do_not_wrap_at_common_mac_widths():
    for width,height in [(82,18),(92,28),(104,22),(120,22),(120,28)]:
        body=node._dash_render(_dash_fixture(),width,height=height,ansi=False)
        assert node._dash_visual_rows(body,width) <= height
        assert all(len(line) <= width for line in body.splitlines())


def test_full_dash_leaves_right_edge_gutter_for_pulse_column():
    body=node._dash_render(_dash_fixture(),92,height=60,ansi=False)
    lines=body.splitlines()
    node_header=next(line for line in lines if "PULSE" in line and "MODEL" in line)
    assert len(node_header) <= 91
    node_rows=[line for line in lines if line.startswith("3090") or line.startswith("m3 ")]
    assert node_rows
    assert all(len(line) <= 91 for line in node_rows)


def test_purpose_label_is_raw_evidence_not_single_score():
    model={"benchmark":{"tested_at":node.now(),"exact":True,"ttft":1.0,"rate":60.0,
                        "reasoning":2,"tools":3,"agent":True}}
    label=node._purpose_label(model,compact=True)
    assert "RFX3/3" in label
    assert "RSN2/3" in label
    assert "T3/3" in label
    assert "A✓" in label
