from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]


def test_local_media_source_stays_native_path():
    text=(ROOT/'look'/'lk').read_text()
    block=text[text.index('def _media_entry_source'):text.index('def _media_write_m3u')]
    assert 'return str(target.resolve())' in block
    assert 'as_uri()' not in block


def test_mpv_logs_are_retained_for_player_failures():
    text=(ROOT/'look'/'lk').read_text()
    assert 'MEDIA_MPV_LOG=STATE_DIR/"media_mpv.log"' in text
    assert 'f"--log-file={MEDIA_MPV_LOG}"' in text
    assert 'def _media_tail_player_log' in text


def test_media_doctor_probes_decode_edge():
    text=(ROOT/'look'/'lk').read_text()
    assert 'def _media_doctor()' in text
    assert '"--ao=null"' in text
    assert '"--length=0.25"' in text
    assert 'if raw in {"doctor","diagnose","debug"}: return _media_doctor()' in text
