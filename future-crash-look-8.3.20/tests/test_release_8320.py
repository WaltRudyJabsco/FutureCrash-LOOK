from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def test_cursor_selection_uses_object_action_footer():
    text=(ROOT/'look/look_renderer.py').read_text()
    block=text.split('elif cursoring:',1)[1].split('elif query:',1)[0]
    for label in ('Tab mark','C Copy To','M Move To','R remove','E edit','O open with'):
        assert label in block
    assert "BROWSE{RESET}" not in block

def test_player_uses_ascii_safe_art_renderer():
    lk=(ROOT/'look/lk').read_text()
    art=(ROOT/'look/media_art.py').read_text()
    assert '_media_player_art_lines(entry,art_w,6)' in lk
    assert "--symbols=ascii" in art
    assert "--colors=none" in art

def test_media_info_progresses_to_native_art_without_blocking():
    lk=(ROOT/'look/lk').read_text()
    assert 'native_art.request(cover' in lk
    assert 'native_art.paint_ready()' in lk
    assert 'watched=[fd]+' in lk

def test_auto_preview_is_mid_sized_not_original_or_tiny():
    text=(ROOT/'look/look_renderer.py').read_text()
    assert 'right_w=min(46,max(34,width//3))' in text
