from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def test_comfy_vram_release_surface():
    text=(ROOT/'look/lk').read_text()
    assert 'def _comfy_unload(' in text
    assert '"unload_models":True' in text
    assert '"free_memory":True' in text
    assert '"auto_unload":True' in text

def test_endpoint_cli_has_stale_daemon_fallback():
    text=(ROOT/'core/node.py').read_text()
    assert 'def _endpoint_allow_cli_fallback(' in text
    assert 'if "404" not in str(exc): raise' in text

def test_transport_marks_unpaired_tailscale():
    text=(ROOT/'core/node.py').read_text()
    assert 'active="TAILSCALE*"' in text
    assert 'not directly paired/trusted' in text
