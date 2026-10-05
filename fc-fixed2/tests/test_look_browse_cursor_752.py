from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
RENDERER=(ROOT/'look'/'look_renderer.py').read_text(encoding='utf-8')
LK=(ROOT/'look'/'lk').read_text(encoding='utf-8')


def test_unfiltered_arrows_enter_browse_cursor_instead_of_scrolling_lines():
    assert "matches=candidates(''); selected=0; cursoring=bool(matches)" in RENDERER
    assert "matches=candidates(''); selected=max(0,len(matches)-1); cursoring=bool(matches)" in RENDERER
    assert "elif key in {'j','\\x1b[B'}: top=" not in RENDERER
    assert "elif key in {'k','\\x1b[A'}: top=" not in RENDERER


def test_browse_cursor_preserves_static_grid_renderer():
    assert "browse_rebuild=lambda h=None,m=None,w=None: build_view" in RENDERER
    assert "interactive_rows=False" in RENDERER
    assert "if cursoring and browse_rebuild:" in RENDERER


def test_filter_selection_keeps_one_candidate_per_row_contract():
    assert "interactive_rows=True" in RENDERER
    assert "if interactive_rows:" in RENDERER


def test_nerd_icons_are_default_and_classic_remains_optional():
    assert 'data={"icons":"nerd","preview":"ascii"}' in LK
    assert '("icons","FILES","File icons"' in LK
    assert "if _ICON_MODE!='nerd':" in RENDERER
    assert "return '◆'" in RENDERER
    assert "return '\\uf07b'" in RENDERER


def test_cursor_follow_uses_actual_rendered_list_height():
    # Selection visibility and page slicing must share one viewport height.
    # Narrow terminals reserve rows for the preview below the file list.
    assert "list_height=list_usable" in RENDERER
    assert "list_height=max(3,list_usable-preview_h-1)" in RENDERER
    assert "elif focus_row >= top+list_height:" in RENDERER
    assert "page=current[top:top+list_height]" in RENDERER
    assert "focus_row=selected//cols" not in RENDERER
    assert "cursor_row=selected//cols" not in RENDERER
