from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def test_stale_local_media_does_not_proxy_to_itself():
    text=(ROOT/'look'/'lk').read_text()
    block=text[text.index('def _media_entry_source'):text.index('def _media_write_m3u')]
    assert '_media_local_node_names' in text
    assert 'stale local catalog path:' in block
    assert '/v1/media/item?' in block

def test_media_root_relocation_is_explicit_and_deduplicating():
    text=(ROOT/'look'/'lk').read_text()
    assert 'def _media_relocate_root' in text
    assert 'lk media scan --relocate OLD_ROOT NEW_ROOT' in text
    block=text[text.index('def _media_relocate_root'):text.index('def _media_scan_command')]
    assert 'row.get("root")' in block
    assert 'media_core.scan_root(target,library)' in block

def test_mpv_ipc_request_id_is_integer():
    text=(ROOT/'look'/'lk').read_text()
    block=text[text.index('def _media_mpv_request'):text.index('def _media_mpv_property')]
    assert 'int(time.time_ns() & 0x7fffffff)' in block
    assert 'uuid.uuid4().hex[:8]' not in block
