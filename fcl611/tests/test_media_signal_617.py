from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]


def test_playback_uses_catalog_id_proxy_not_nested_fabric_cli():
    text=(ROOT/'look'/'lk').read_text()
    block=text[text.index('def _media_entry_source'):text.index('def _media_write_m3u')]
    assert '/v1/media/item?' in block
    assert '_media_identify_catalog_entry' not in block
    assert '_media_fabric_cli' not in block


def test_node_serves_catalog_id_media_with_head_and_get():
    text=(ROOT/'core'/'node.py').read_text()
    assert 'def _serve_media_item(' in text
    assert 'def _local_media_entry(' in text
    head=text[text.index('    def do_HEAD(self):'):text.index('    def do_GET(self):')]
    get=text[text.index('    def do_GET(self):'):text.index('    def do_POST(self):')]
    assert '/v1/media/item' in head
    assert '/v1/media/item' in get


def test_signal_abstains_from_generic_filler_art():
    text=(ROOT/'signal-window'/'server.py').read_text()
    assert 'return None,"none"' in text
    assert 'Never draw generic mountains, a sun, or a landscape' in text
    assert 'routine_media=' in text


def test_player_card_can_show_stopped_queue():
    text=(ROOT/'signal-window'/'app.js').read_text()
    assert "(!active&&d?.state==='stopped')" not in text
