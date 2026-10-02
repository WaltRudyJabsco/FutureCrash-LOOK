from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

def test_tailcat_advertises_overlay_endpoints():
    src=(ROOT/'core/tailcat.py').read_text()
    assert 'def _tailscale_endpoints(port: int)' in src
    assert 'TailscaleIPs' in src
    assert 'DNSName' in src
    assert 'endpoints.extend(_tailscale_endpoints(port))' in src

def test_browser_media_reuses_item_transport():
    node=(ROOT/'core/node.py').read_text()
    assert 'def _serve_media_item(self,target,entry_id,path_hint="",*,head=False,representation="original")' in node
    assert 'representation=="browser"' in node
    assert 'url=base+"/v1/media/item?"' in node
    assert 'def _serve_media_browser' in node
    assert 'representation="browser"' in node

def test_signal_broad_video_choices_are_pending():
    src=(ROOT/'signal-window/server.py').read_text()
    assert 'def _broad_video_prompt' in src
    assert 'def _signal_pending_media' in src
    assert 'R  Surprise me' in src
    assert 'M  More' in src
    assert 'deterministic-media-choice' in src

def test_albert_preserves_video_extension_and_more_choice():
    src=(ROOT/'albert/server.py').read_text()
    assert 'if result_type=="video"' in src
    assert 'title += suffix' in src
    assert '"M  More"' in src
