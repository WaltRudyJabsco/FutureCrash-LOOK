from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
LK=(ROOT/'look/lk').read_text(); RENDER=(ROOT/'look/look_renderer.py').read_text(); NODE=(ROOT/'core/node.py').read_text(); INGRESS=(ROOT/'core/ingress.py').read_text(); ALBERT=(ROOT/'albert/server.py').read_text(); AUI=(ROOT/'albert/index.html').read_text(); SIGNAL=(ROOT/'signal-window/server.py').read_text(); SUI=(ROOT/'signal-window/app.js').read_text()

def test_media_hide_ancestor_picker_is_counted_and_root_guarded():
    assert 'def _media_tree_candidates(row, rows):' in LK
    assert 'def _media_choose_hide_directory(row, rows, fd):' in LK
    assert 'MEDIA ROOT · hide all' in LK
    assert '_media_choose_hide_directory(visible[idx],rows,fd)' in LK

def test_media_find_modern_navigation_and_hot_loop_cache():
    for token in ('"shiftup"','"shiftdown"','"shiftleft"','"shiftright"','"home"','"end"'): assert token in LK
    assert 'next_view_key=(query,show_all,show_hidden)' in LK
    collapse=LK[LK.index('def _media_collapse'):LK.index('def _media_tree_candidates')]
    assert '.exists()' not in collapse

def test_sticky_header_focus_follows_real_viewport():
    assert 'focus_row=selected' in RENDER
    assert 'cursoring' not in RENDER
    assert 'elif focus_row >= top+list_usable:' in RENDER

def test_fabric_browser_video_representation_is_cached_and_source_safe():
    assert 'def _browser_media_source(self, entry_id, path_hint=""):' in NODE
    assert 'browser-media' in NODE and 'libx264' in NODE and 'yuv420p' in NODE and 'aac' in NODE
    assert 'os.replace(tmp,target)' in NODE and '"/v1/media/browser"' in NODE and '"/v1/media/browser"' in INGRESS

def test_browsers_request_video_representation():
    assert "kind:media.tagName==='VIDEO'?'video':'audio'" in AUI
    assert "'/api/media/browser' if kind=='video'" in ALBERT
    assert "kind:browserIsVideo(entry)?'video':'audio'" in SUI
    assert 'route="/api/media/browser" if kind=="video"' in SIGNAL

def test_albert_broad_video_is_pending_choice_not_random_execution():
    assert 'def _broad_video_choices(session):' in ALBERT
    assert 'broad_video=bool(re.fullmatch' in ALBERT
    assert '"R  Surprise me"' in ALBERT
    assert 'pending choice' in ALBERT
    assert 'choose_random={"r","random","surprise me","you choose"' in ALBERT
