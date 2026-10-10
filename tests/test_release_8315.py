from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
NODE=(ROOT/'core/node.py').read_text()
SERVE=(ROOT/'core/tailscale_serve.py').read_text()

def test_tailscale_backend_is_woken_before_serve_reconcile():
    assert 'def ensure_backend' in SERVE
    assert '"-gja", "Tailscale"' in SERVE
    assert 'backend_ok, backend_detail = ensure_backend(binary)' in SERVE

def test_media_catalog_refreshes_discovery_and_tries_all_peer_routes():
    assert 'try: _refresh_media_peers_background()' in NODE
    assert 'MEDIA_CATALOG_PEER_TIMEOUT = 8.0' in NODE
    assert 'ThreadPoolExecutor' in NODE
    assert 'as_completed' in NODE
    assert '"/v1/media/catalog"' in NODE
    assert 'for base in _peer_bases(peer)' in NODE

def test_transport_hostname_does_not_replace_fabric_label():
    assert '"hostname":str(row.get("hostname") or "")' in NODE
    assert 'name = (peer.get("name") or (ad.get("identity") or {}).get("name"))' in NODE
    assert 'row["node"] = name' in NODE
