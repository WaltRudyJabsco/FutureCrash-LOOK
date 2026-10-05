from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]


def test_native_classics_and_arts_sources_remain_present():
    lk=(ROOT/'look/lk').read_text()
    albert=(ROOT/'albert/server.py').read_text()
    assert 'https://allclassical.streamguys1.com/ac128kmp3' in lk
    assert 'https://www.classicartsshowcase.org/watch-classic-arts-showcase/' in lk
    assert 'https://allclassical.streamguys1.com/ac128kmp3' in albert


def test_core_media_item_forwarding_remains_item_transport():
    node=(ROOT/'core/node.py').read_text()
    start=node.index('def _serve_media_item')
    end=node.index('def _serve_media_artifact',start)
    block=node[start:end]
    assert 'base+"/v1/media/item?"' in block
    assert 'base+"/v1/media/audio?"' not in block


def test_look_remote_catalog_uses_item_before_artifact_fallback():
    lk=(ROOT/'look/lk').read_text()
    start=lk.index('def _media_entry_source')
    end=lk.index('def _media_wait_for_local_queue',start)
    block=lk[start:end]
    assert block.index('if node and entry_id:') < block.index('if digest:')
