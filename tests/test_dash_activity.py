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
