from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

def test_release_versions_are_synchronized():
    assert (ROOT/'VERSION').read_text().strip()=='6.3.4'
    assert (ROOT/'look/VERSION').read_text().strip()=='6.3.4'
    for rel in ('core/node.py','core/tailcat.py','core/ingress.py'):
        text=(ROOT/rel).read_text()
        assert '6.3.4' in text
        assert '6.1.8' not in text

def test_signal_browser_is_default_media_endpoint():
    js=(ROOT/'signal-window/app.js').read_text()
    assert "let selectedMediaOutput='browser'" in js
    assert "localStorage.getItem('signal.media.node')" not in js
    assert "localStorage.setItem('signal.media.node'" not in js
    assert 'media_endpoint:selectedMediaOutput' in js
    assert "d.media&&selectedMediaOutput==='browser'" in js

def test_signal_server_distinguishes_source_node_from_browser_output():
    py=(ROOT/'signal-window/server.py').read_text()
    assert 'media_endpoint=str(d.get("media_endpoint") or "").strip()' in py
    assert 'browser_target=(media_endpoint=="browser" or not media_endpoint)' in py
    assert 'Playing {query} on this device.' in py
