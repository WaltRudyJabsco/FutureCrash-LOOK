from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
RENDERER=(ROOT/'look'/'look_renderer.py').read_text(encoding='utf-8')


def test_unfiltered_arrows_enter_filter_not_legacy_select_cursor():
    assert "elif key in {'j','\\x1b[B'} and candidates:" in RENDERER
    assert "elif key in {'k','\\x1b[A'} and candidates:" in RENDERER
    assert "filtering=True; query=''; refresh_filter()" in RENDERER
    assert "matches=candidates(''); selected=0; cursoring=bool(matches)" not in RENDERER
    assert "matches=candidates(''); selected=max(0,len(matches)-1); cursoring=bool(matches)" not in RENDERER


def test_legacy_cursor_state_is_not_entered_anywhere():
    assert 'cursoring=True' not in RENDERER
    assert 'cursoring=bool(' not in RENDERER
