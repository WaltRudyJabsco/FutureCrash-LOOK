from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
LK=(ROOT/'look'/'lk').read_text()
GAMES=(ROOT/'look'/'games.py').read_text()
ALBERT=(ROOT/'albert'/'index.html').read_text()
SIGNAL=(ROOT/'signal-window'/'app.js').read_text()

def test_hide_directory_is_immediate_parent_not_media_root():
    block=LK.split('def _media_hide(rows, tree=False):',1)[1].split('def _media_unhide',1)[0]
    assert 'Path(path).parent' in block
    assert 'row.get("root") if tree' not in block

def test_shift_u_removes_visibility_rule_and_info_explains_rule():
    assert 'def _media_unhide(rows):' in LK
    assert 'if key=="U" and chosen:' in LK
    assert 'Hidden by' in LK
    assert 'D hide tree (dir) · U unhide' in LK

def test_tic_tac_toe_uses_large_sprites_and_red_blue_turns():
    block=GAMES.split('def render_ttt',1)[1].split('def play_ttt',1)[0]
    assert '██   ██' in block and '█████' in block
    assert "'BLUE' if turn=='X' else 'RED'" in block

def test_backgammon_uses_red_blue_visual_language():
    block=GAMES.split('def render_bg',1)[1].split('def play_backgammon',1)[0]
    assert 'RED+"●"' in block
    assert 'OFF  BLUE:' in block and 'RED:' in block

def test_gtnw_renderer_scales_to_terminal_without_changing_simulation():
    block=LK.split('def _gtnw_render',1)[1].split('def _gtnw_make_sim',1)[0]
    assert 'shutil.get_terminal_size' in block
    assert 'canvas_w' in block and 'canvas_h' in block

def test_albert_fabric_video_gets_ticketed_native_video_element():
    video=ALBERT.split("if(f.type==='video')",1)[1].split("if(f.type==='image')",1)[0]
    assert 'data-media-id' in video and '<video controls autoplay playsinline' in video
    assert "mediaStep('${f.id}',1)" in video

def test_signal_browser_output_supports_audio_and_video():
    assert "const browserVideo=document.createElement('video')" in SIGNAL
    assert 'function browserIsVideo(entry)' in SIGNAL
    assert 'browserIsVideo(entry)?browserVideo:browserAudio' in SIGNAL
