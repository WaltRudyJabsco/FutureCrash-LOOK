from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
SRC=(ROOT/'look/look_renderer.py').read_text()
LK=(ROOT/'look/lk').read_text()

def test_release_version():
    assert (ROOT/'VERSION').read_text().strip()=='8.10.0'

def test_selected_browse_item_uses_inspection_pane():
    assert 'elif filtering and picked:' in SRC
    assert 'elif filtering and picked and width>=96:' in SRC
    assert 'cursoring' not in SRC and 'selecting' not in SRC

def test_destination_picker_returns_to_editable_line():
    assert 'def _destination_picker(start_dir:Path)' in SRC
    assert "down/right opens LOOK Destination" in SRC
    assert 'picker_root=current_dir' in SRC
    assert "else visible[selected].resolve()" in SRC
    assert "return chosen" in SRC

def test_media_info_has_cover_fallback():
    assert 'def _media_cover_path(row):' in LK
    assert 'def _media_cover_lines(row,width,height=11,background_remote=False):' in LK
    assert 'details=_media_detail_lines(visible[idx],detail_w)' in LK
