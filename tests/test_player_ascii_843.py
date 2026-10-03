from pathlib import Path
import re

ROOT=Path(__file__).resolve().parents[1]
LK=(ROOT/'look/lk').read_text()


def test_real_player_renderer_uses_ascii_helper_and_11_rows():
    start=LK.index('def _media_player_render')
    end=LK.index('\ndef media_player', start)
    block=LK[start:end]
    assert '_media_player_art_lines(entry,art_w,11)' in block
    assert '_media_cover_lines(entry,art_w,6)' not in block
    assert '"", "", "",' in block


def test_player_helper_never_calls_chafa_symbol_renderer():
    start=LK.index('def _media_player_art_lines')
    end=LK.index('\ndef _media_detail_lines', start)
    block=LK[start:end]
    assert 'media_art.ascii_lines' in block
    assert 'media_art.symbol_lines' not in block


def test_ascii_palette_is_strict_one_byte_ascii():
    art=(ROOT/'look/media_art.py').read_text()
    assert "ramp=' .:-=+*#%@'" in art
    ramp=' .:-=+*#%@'
    assert all(ord(ch) < 128 for ch in ramp)
