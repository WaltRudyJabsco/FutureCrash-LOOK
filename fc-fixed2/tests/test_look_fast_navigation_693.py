from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
SOURCE=(ROOT/'look/look_renderer.py').read_text()


def test_shift_arrows_are_native_navigation_aliases():
    # Standard xterm-style Shift+Arrow sequences, verified on macOS and Linux.
    assert "'\\x1b[1;2B'" in SOURCE  # Shift-Down: page down
    assert "'\\x1b[1;2A'" in SOURCE  # Shift-Up: page up
    assert "key=='\\x1b[1;2D'" in SOURCE  # Shift-Left: top
    assert "key=='\\x1b[1;2C'" in SOURCE  # Shift-Right: bottom


def test_browse_g_toggles_ends_without_stealing_uppercase_go():
    assert "elif key=='g': top=max(0,len(current)-usable) if top==0 else 0" in SOURCE
    assert "elif key=='G' and on_go and current_dir is not None:" in SOURCE


def test_filter_keeps_uppercase_g_as_go():
    assert "elif key=='G' and matches:" in SOURCE
