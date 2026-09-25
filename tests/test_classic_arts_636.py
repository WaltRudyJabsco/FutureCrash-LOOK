from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

def test_classic_arts_uses_default_browser_in_look():
    lk=(ROOT/'look/lk').read_text()
    block=lk[lk.index('if raw in {"arts","showcase","classic-arts"}'):][:700]
    assert 'classicartsshowcase.org/watch-classic-arts-showcase/' in block
    assert '_tool_open_url(url)' in block
    assert '_media_launch_stream' not in block
    assert 'master_3000k.m3u8' not in block

def test_albert_keeps_classic_arts_fold():
    html=(ROOT/'albert/index.html').read_text()
    assert 'Classic Arts Showcase' in html
    assert 'CLASSIC_ARTS' in html
