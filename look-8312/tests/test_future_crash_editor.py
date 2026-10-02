import importlib.util
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
SPEC=importlib.util.spec_from_file_location("future_crash_ui", ROOT/"future-crash"/"future_crash.py")
MOD=importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name]=MOD
SPEC.loader.exec_module(MOD)


def test_edit_line_cursor_tracks_logical_deletion():
    line=MOD.render_edit_line("this is a tesst", 14, 40)
    assert "this is a tess_t" in line
    edited="this is a tesst"[:13]+"this is a tesst"[14:]
    line2=MOD.render_edit_line(edited, 13, 40)
    assert "this is a tes_t" in line2
    assert len(line2)==40


def test_edit_line_long_input_keeps_cursor_visible_and_fixed_width():
    text="abcdefghijklmnopqrstuvwxyz0123456789"
    line=MOD.render_edit_line(text, 8, 16)
    assert "_" in line
    assert len(line)==16
    line2=MOD.render_edit_line(text, len(text), 16)
    assert line2.rstrip().endswith("_")
    assert len(line2)==16


def test_edit_line_clamps_cursor():
    assert MOD.render_edit_line("abc", 99, 8).startswith("> abc_")
