from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def test_shift_object_tools_are_wired_in_all_selection_states():
    text=(ROOT/'look/look_renderer.py').read_text()
    assert "key in {'C','M','D'}" in text
    assert "key=='R'" in text
    assert 'R rename' in text and 'D delete' in text

def test_batch_rename_has_hash_sequence_and_collision_guard():
    text=(ROOT/'look/look_renderer.py').read_text()
    assert "batch rename needs # numbering" in text
    assert "zfill(len(m.group(0)))" in text
    assert "rename would create duplicate names" in text
    assert "already exists ·" in text

def test_media_find_startup_feedback_and_compact_player_art():
    lk=(ROOT/'look/lk').read_text()
    assert 'LOOK MEDIA FIND · opening local + Fabric catalogs' in lk
    assert 'if inner>=42 else 0' in lk
