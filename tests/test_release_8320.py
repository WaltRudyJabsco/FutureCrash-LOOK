from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def test_cursor_selection_uses_object_action_footer():
    text=(ROOT/'look/look_renderer.py').read_text()
    block=text.split('elif cursoring:',1)[1].split('elif query:',1)[0]
    for label in ('Tab mark','C Copy To','M Move To','⇧R rename','⇧D delete','E edit','O open with'):
        assert label in block
    assert "BROWSE{RESET}" not in block

def test_player_restores_known_good_8319_art_renderer():
    lk=(ROOT/'look/lk').read_text()
    assert 'art=_media_cover_lines(entry,art_w,6) if art_w else []' in lk

def test_media_find_does_not_overlay_art_asynchronously():
    lk=(ROOT/'look/lk').read_text()
    start=lk.index('def _media_selector(')
    end=lk.index('def _media_find_command', start)
    selector=lk[start:end]
    assert 'native_art=NativePreviewController()' not in selector
    assert 'native_art.request(' not in selector
    assert 'native_art.paint_ready()' not in selector

def test_auto_preview_is_mid_sized_not_original_or_tiny():
    text=(ROOT/'look/look_renderer.py').read_text()
    assert 'right_w=min(60,max(40,(width*2)//5))' in text
