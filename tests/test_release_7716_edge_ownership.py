from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]


def test_macos_installer_retires_only_known_stale_fabric_node():
    text=(ROOT/'install.sh').read_text()
    assert 'retire_stale_macos_node_listener()' in text
    assert 'lsof -nP -t -iTCP@127.0.0.1:7332 -sTCP:LISTEN' in text
    assert '$HOME/.local/bin/fcl-node' in text
    assert '$HOME/.local/share/future-crash-look/core/node.py' in text
    assert 'localhost :7332 is owned by an unmanaged process' in text
    assert 'kill -TERM "$pid"' in text


def test_albert_catalog_browser_path_matches_signal_api_boundary():
    text=(ROOT/'albert/server.py').read_text()
    assert "src='/api/media/audio?'+urlencode({'node':media_node,'id':item_id,'ticket':ticket})" in text
    assert "if path in {'/api/media/audio','/v1/media/item'}:" in text
    assert '_proxy_media_item(self,node,item_id,head=True)' in text
    assert '_proxy_media_item(self,node,item_id)' in text
