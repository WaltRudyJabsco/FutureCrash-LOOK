from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]


def test_local_queue_gets_one_bounded_automount_preflight():
    text=(ROOT/'look'/'lk').read_text()
    block=text[text.index('def _media_wait_for_local_queue'):text.index('def _media_write_m3u')]
    assert 'Probe' in block or 'probe' in block
    assert 'time.sleep' in block
    assert 'any(path.is_file() for path in paths)' in block
    assert '0.55' in block


def test_preflight_is_once_per_queue_not_once_per_track():
    text=(ROOT/'look'/'lk').read_text()
    write=text[text.index('def _media_write_m3u'):text.index('def _media_mpv_binary')]
    assert '_media_wait_for_local_queue(queue)' in write
    source=text[text.index('def _media_entry_source'):text.index('def _media_wait_for_local_queue')]
    assert 'time.sleep' not in source
