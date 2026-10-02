from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def test_albert_video_ticket_parses_kind_before_route():
    s=(ROOT/'albert/server.py').read_text()
    fn=s[s.index('def _media_ticket_request'):s.index('def do_HEAD',s.index('def _media_ticket_request'))]
    assert "kind=str(params.get('kind',['audio'])[0] or 'audio').casefold()" in fn
    assert "if kind not in {'audio','video'}" in fn
    assert "if kind=='video' else '/api/media/audio'" in fn

def test_peer_advertisement_allows_wake_latency():
    s=(ROOT/'core/node.py').read_text()
    assert 'base+"/v1/advertisement",timeout=3.0' in s

def test_fabric_catalog_reports_unadvertised_known_peers():
    s=(ROOT/'core/node.py').read_text()
    assert 'peer discovered/trusted but advertisement unavailable' in s
    assert 'timeout=12.0' in s
