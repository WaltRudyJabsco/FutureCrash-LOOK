from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def test_cross_node_handoff_streams_source_paths():
    text=(ROOT/'core/node.py').read_text()
    block=text[text.index('def _fabric_media_move'):text.index('def _local_artifact_catalog') ]
    assert 'source_path' in block
    assert '/v1/media/audio?index=' in block
    assert '_remote_url(snapshot,source' in block

def test_signal_browser_endpoint_never_calls_media_move():
    js=(ROOT/'signal-window/app.js').read_text()
    start=js.index("if(next==='browser')")
    end=js.index('const nextNode=',start)
    assert '/api/media/move' not in js[start:end]
    assert 'browserPlayIndex' in js[start:end]

def test_signal_uses_explicit_endpoint_buttons():
    js=(ROOT/'signal-window/app.js').read_text()
    assert "className='media-output-choice'" in js
    assert "target:'browser'" in js
    assert "target:nodeTarget(row.node)" in js
    assert "document.createElement('select')" not in js[js.index('function renderMedia'):js.index('async function mediaControl')]

def test_look_player_accepts_fabric_http_queue_sources():
    text=(ROOT/'look/lk').read_text()
    block=text[text.index('def _media_entry_source'):text.index('def _media_write_m3u')]
    assert 'path.startswith(("http://","https://"))' in block
    assert 'return path' in block
