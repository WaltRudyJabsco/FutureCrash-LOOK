from pathlib import Path
import importlib.util
import sys

ROOT=Path(__file__).resolve().parents[1]
SPEC=importlib.util.spec_from_file_location('look_renderer',ROOT/'look'/'look_renderer.py')
mod=importlib.util.module_from_spec(SPEC); sys.modules[SPEC.name]=mod; SPEC.loader.exec_module(mod)


def test_cursor_follow_uses_one_candidate_per_rendered_row():
    # 27 visible rows: the 28th selected item must scroll exactly one row.
    assert mod._follow_selection(0, 26, 27, 100) == 0
    assert mod._follow_selection(0, 27, 27, 100) == 1
    assert mod._follow_selection(1, 28, 27, 100) == 2


def test_cursor_follow_tracks_upward_and_clamps_ends():
    assert mod._follow_selection(20, 19, 27, 100) == 19
    assert mod._follow_selection(73, 99, 27, 100) == 73
    assert mod._follow_selection(50, 0, 27, 10) == 0


def test_browse_cursor_has_no_legacy_column_division():
    source=(ROOT/'look'/'look_renderer.py').read_text(encoding='utf-8')
    pager=source[source.index('def pager('):source.index('\ndef main(')]
    assert 'selected//cols' not in pager
    assert '_follow_selection(top,selected,list_usable,len(current))' in pager
