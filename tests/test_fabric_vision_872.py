from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
LK=(ROOT/'look'/'lk').read_text()


def test_local_vision_bypasses_unified_node():
    assert 'def _vision_screen_local(' in LK
    fetch=LK.split('def _vision_screen_fetch(',1)[1].split('\ndef ',1)[0]
    assert 'if not str(node or "").strip():' in fetch
    assert 'return _vision_screen_local(previous_hash,max_width,quality,display)' in fetch
    # HTTP is retained only after the local fast path for real Fabric hops.
    assert fetch.index('_vision_screen_local') < fetch.index('127.0.0.1:7332/v1/vision/screen')


def test_local_capture_loads_shared_fabric_vision_module():
    local=LK.split('def _vision_screen_local(',1)[1].split('\ndef ',1)[0]
    assert '.local/share/future-crash-look/core' in local
    assert 'from fabric_vision import capture_screen' in local
    assert 'payload=capture_screen(' in local
