from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
SRC=(ROOT/'look'/'look_renderer.py').read_text()
LK=(ROOT/'look'/'lk').read_text()


def test_preview_view_is_same_pager_state():
    assert "preview_view=False" in SRC
    assert "if key=='V' and matches:" in SRC
    assert "preview_view=not preview_view" in SRC
    assert "if preview_view and filtering and picked:" in SRC
    assert "preview_rows(picked,width,list_usable)" in SRC


def test_preview_view_marks_existing_marked_set():
    assert "if preview_view and key==' ' and matches:" in SRC
    assert "if rp in marked: marked.remove(rp)" in SRC
    assert "else: marked.add(rp)" in SRC


def test_escape_leaves_preview_before_clearing_filter():
    needle=r"elif key=='\x1b':" + "\n                    if preview_view:\n                        preview_view=False\n                    else:\n                        query=''; filtering=False; selecting=False; refresh_filter()"
    assert needle in SRC


def test_simple_preview_architecture_stays_canonical():
    assert "data={'icons':'nerd','preview':'ascii'}" in SRC
    assert "--format=symbols" in SRC
    assert '_terminal_graphics_format' not in SRC
    assert '--format=kitty' not in SRC
    assert '--format=iterm' not in SRC
    assert '--format=sixels' not in SRC
    assert 'preview_deadline' not in SRC
    assert 'preview_worker' not in SRC
    assert '"preview":"ascii"' in LK


def test_release_version():
    assert (ROOT/'VERSION').read_text().strip()=='8.3.5'
