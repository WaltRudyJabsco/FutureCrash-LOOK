from pathlib import Path
import tempfile
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'look'))
import media_core


def test_m4p_is_always_protected():
    assert media_core.protected_media_reason({'path':'/x/song.m4p','format':'m4p'}).startswith('protected')


def test_fairplay_style_drmi_atom_is_detected():
    with tempfile.TemporaryDirectory() as td:
        p=Path(td)/'movie.m4v'
        p.write_bytes(b'\x00'*64+b'drmi'+b'\x00'*64)
        assert 'protected' in media_core.protected_media_reason({'path':str(p),'format':'m4v'})


def test_common_encryption_box_pair_is_detected():
    with tempfile.TemporaryDirectory() as td:
        p=Path(td)/'movie.mp4'
        p.write_bytes(b'ftyp'+b'\x00'*32+b'sinf'+b'\x00'*32+b'schm')
        assert 'protected' in media_core.protected_media_reason({'path':str(p),'format':'mp4'})


def test_ordinary_mov_is_not_falsely_marked_protected():
    with tempfile.TemporaryDirectory() as td:
        p=Path(td)/'home.mov'
        p.write_bytes(b'ftypqt  '+b'\x00'*256)
        assert media_core.protected_media_reason({'path':str(p),'format':'mov'}) == ''


def test_look_uses_runtime_safe_selector_and_launch_guard():
    source=(ROOT/'look'/'lk').read_text()
    assert 'def _media_select_runtime_safe' in source
    assert 'protected/restricted item(s) skipped' in source
    assert 'media_core.protected_media_reason(entry)' in source
