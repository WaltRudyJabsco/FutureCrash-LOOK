from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

def test_look_remote_catalog_items_use_item_edge():
    src=(ROOT/"look/lk").read_text()
    block=src[src.index("def _media_entry_source"):src.index("def _media_wait_for_local_queue")]
    assert "/v1/media/item?" in block
    assert '"node":node,"id":entry_id' in block

def test_signal_facade_preserves_item_vs_queue_semantics():
    src=(ROOT/"signal-window/server.py").read_text()
    block=src[src.index("def _proxy_media_audio"):src.index("_PRESENTED",src.index("def _proxy_media_audio"))]
    assert 'path="/v1/media/item"' in block
    assert 'path="/v1/media/audio"' in block
    assert 'if item_id:' in block

def test_signal_browser_uses_facade_not_fabric_path_directly():
    js=(ROOT/"signal-window/app.js").read_text()
    assert '/api/media/audio?node=' in js
    assert '&id=${encodeURIComponent(itemId)}' in js

def test_ingress_streams_both_media_edges():
    src=(ROOT/"core/ingress.py").read_text()
    assert '"/v1/media/audio"' in src
    assert '"/v1/media/item"' in src
