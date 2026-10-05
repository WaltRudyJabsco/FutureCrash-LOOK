from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'look'))
import look_renderer as lr


def test_selection_never_leaves_27_row_viewport_down_and_up():
    count=130
    visible=27
    top=0
    for selected in range(count):
        top=lr.follow_viewport(selected,top,count,visible)
        assert top <= selected < top+visible
    for selected in range(count-1,-1,-1):
        top=lr.follow_viewport(selected,top,count,visible)
        assert top <= selected < top+visible


def test_next_item_after_bottom_scrolls_exactly_one_row():
    top=0
    for selected in range(28):
        old=top
        top=lr.follow_viewport(selected,top,130,27)
        if selected < 27:
            assert top == 0
        else:
            assert old == 0 and top == 1


def test_narrow_footer_wrap_is_not_hidden_inside_fixed_five_line_budget():
    parts=['↑/↓ move','Tab mark','Enter/→ open','B clipboard','B Copy','T Cut','P Paste',
           'C Copy To','M Move To','⇧R rename','⇧D delete','L LO context','X clear set',
           'E edit','O open with','Y path','G go','← parent','Esc clear','q quit']
    # This is the terminal shape that exposed rows underneath the footer.
    assert len(lr.action_footer(parts,60)) >= 5


def test_interactive_renderer_has_no_legacy_column_cursor_math():
    source=(ROOT/'look'/'look_renderer.py').read_text(encoding='utf-8')
    assert 'selected//cols' not in source
    assert 'cursor_row=selected//cols' not in source
    assert 'focus_row=selected//cols' not in source
