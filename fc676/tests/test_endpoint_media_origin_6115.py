from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def test_browser_play_prepares_without_starting_source_player():
    py=(ROOT/'signal-window/server.py').read_text()
    assert 'operation="prepare" if prepare else "play"' in py
    assert 'state=_media_play(query,media_node,prepare=browser_target,intent=normalized)' in py
    assert 'state["output_target"]="browser" if browser_target else media_endpoint' in py

def test_prepared_queue_is_non_mutating():
    lk=(ROOT/'look/lk').read_text()
    start=lk.index('def _media_prepare_command')
    end=lk.index('def _media_play_command',start)
    block=lk[start:end]
    assert 'media_core.new_session' in block
    assert '_media_launch_session' not in block
    assert '_media_queue_append' not in block

def test_browser_streams_prepared_items_by_identity_not_source_session_index():
    js=(ROOT/'signal-window/app.js').read_text()
    assert "const itemId=String(entry.id||entry.digest||'')" in js
    assert 'id=${encodeURIComponent(itemId)}' in js
    py=(ROOT/'signal-window/server.py').read_text()
    assert 'path="/v1/media/item"' in py

def test_signal_attaches_origin_endpoint_to_media_receipt():
    py=(ROOT/'signal-window/server.py').read_text()
    assert 'origin=self._endpoint() or {}' in py
    assert 'state["origin_endpoint"]=' in py
