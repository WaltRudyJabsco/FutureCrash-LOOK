from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
LK=(ROOT/'look'/'lk').read_text(encoding='utf-8')
NODE=(ROOT/'core'/'node.py').read_text(encoding='utf-8')


def test_player_queue_uses_local_media_artifact_proxy():
    block=LK[LK.index('def _media_entry_source'):LK.index('def _media_write_m3u')]
    assert 'http://127.0.0.1:7332/v1/media/artifact?' in block
    assert '_media_artifact(digest' not in block
    assert 'urllib.parse.urlencode(params)' in block


def test_node_exposes_range_capable_media_artifact_proxy():
    assert 'def _serve_media_artifact(self,target,digest,*,head=False):' in NODE
    assert 'if path == "/v1/media/artifact":' in NODE
    assert 'headers["Range"]=self.headers.get("Range")' in NODE
    assert 'FABRIC_IDENTITY.auth_headers_for_url(url)' in NODE
    assert 'FABRIC_IDENTITY.ssl_context_for_url(url)' in NODE
    assert 'for base in _peer_bases(peer):' in NODE


def test_media_cli_json_error_is_diagnostic_not_opaque():
    block=LK[LK.index('def _media_fabric_cli'):LK.index('def _media_update_identity_for_path')]
    assert 'decoder=json.JSONDecoder()' in block
    assert 'Fabric command returned invalid JSON ·' in block
