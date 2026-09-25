from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def test_classic_arts_prefers_clean_hls_native():
    lk=(ROOT/'look/lk').read_text()
    assert 'classicarts.global.ssl.fastly.net/live/cas/master_3000k.m3u8' in lk
    block=lk[lk.index('if raw in {"arts","showcase","classic-arts"}'):][:900]
    assert '_media_launch_stream' in block
    assert '_tool_open_url' not in block

def test_albert_video_is_fitted_expandable_and_has_fallback():
    html=(ROOT/'albert/index.html').read_text()
    assert 'CLASSIC_ARTS_STREAM' in html
    assert 'object-fit:contain' in html
    assert 'toggleMediaExpand' in html
    assert 'fitScaledPages' in html
    assert 'videoFallback' in html
    assert 'data-fallback' in html

def test_albert_server_returns_stream_and_official_fallback():
    text=(ROOT/'albert/server.py').read_text()
    assert 'CLASSIC_ARTS_STREAM' in text
    assert '"src":CLASSIC_ARTS_STREAM' in text
    assert '"embed":CLASSIC_ARTS' in text
