from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
LK=(ROOT/'look/lk').read_text()
NODE=(ROOT/'core/node.py').read_text()

def test_fabric_catalog_allows_remote_library_time():
    assert 'MEDIA_CATALOG_PEER_TIMEOUT = 3.0' in NODE
    assert 'ThreadPoolExecutor' in NODE
    assert '_peer_json(' in NODE
    assert '"/v1/media/catalog"' in NODE

def test_find_surfaces_partial_fabric_state():
    assert 'FABRIC PARTIAL' in LK
    assert 'unavailable: {failed}' in LK
    assert '_media_selector(rows,"FABRIC MEDIA FIND",query,catalog_meta)' in LK

def test_scan_without_root_discovers_standard_media():
    assert 'candidates=[home/"Music", home/"Movies"]' in LK
    assert 'Media.localized' in LK
    assert 'LOOK MEDIA DISCOVERY' in LK
