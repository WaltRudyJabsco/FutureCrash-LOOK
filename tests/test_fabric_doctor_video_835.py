from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def test_fabric_doctor_is_local_first_and_peer_specific():
    lk=(ROOT/'look/lk').read_text()
    assert 'def _fabric_doctor()' in lk
    assert '127.0.0.1:7332' in lk
    assert '[exe,"media-catalog","--node",name,"--json"]' in lk
    assert 'if sub in {"doctor","diagnose","debug"}: return _fabric_doctor()' in lk

def test_browser_video_daemon_path_and_encoder_fallback():
    node=(ROOT/'core/node.py').read_text()
    assert '"/opt/homebrew/bin"' in node
    assert 'ffmpeg is required for browser video conversion' in node
    assert 'h264_videotoolbox' in node
    assert 'browser video conversion failed' in node

def test_media_find_explains_identity_glyphs():
    lk=(ROOT/'look/lk').read_text()
    assert '◆ SHA · · scanned' in lk
