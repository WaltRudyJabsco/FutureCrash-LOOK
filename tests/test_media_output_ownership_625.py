from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]


def test_native_video_launch_is_deterministic_and_visible():
    text=(ROOT/'look/lk').read_text()
    block=text[text.index('def _media_launch_session'):text.index('def _media_launch_stream')]
    assert '"--no-config"' in block
    assert '"--video=yes"' in block
    assert '"--force-window=immediate"' in block
    assert 'session["player"]="mpv"' in block
    assert 'session["presentation"]="video" if _media_queue_has_video(queue) else "audio"' in block
    assert 'session["launch_argv"]=[str(x) for x in cmd]' in block


def test_signal_exposes_route_and_preserves_browser_default():
    js=(ROOT/'signal-window/app.js').read_text()
    assert "let selectedMediaOutput='browser'" in js
    assert "event('MEDIA · SEARCHING',true)" in js
    assert 'MEDIA ROUTE · ${routeTarget} · ${routePlayer}' in js
    assert "selectedMediaOutput==='browser'?'browser':String(d.media.player||'mpv')" in js


def test_node_advertises_native_video_capability():
    text=(ROOT/'core/node.py').read_text()
    block=text[text.index('def _local_media_output'):text.index('def _local_media_route')]
    assert '"presentation": "native"' in block
    assert '"media.video"' in block
