from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

def test_ingress_supports_head_and_streams_media():
    src=(ROOT/'core'/'ingress.py').read_text()
    assert 'do_HEAD = _relay' in src
    assert '"/v1/media/audio"' in src
    assert 'if self.command != "HEAD"' in src

def test_remote_media_uses_fabric_auth_and_tls_pin():
    src=(ROOT/'core'/'node.py').read_text()
    assert 'headers=FABRIC_IDENTITY.auth_headers_for_url(url)' in src
    assert 'FABRIC_IDENTITY.ssl_context_for_url(url)' in src

def test_endpoint_mutation_has_transport_fallback():
    src=(ROOT/'core'/'node.py').read_text()
    assert 'for base in _peer_bases(peer):' in src
    assert 'endpoint approval transport failed' in src
