from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
LK=(ROOT/'look/lk').read_text(encoding='utf-8')

def test_audio_to_video_restarts_owned_mpv_for_visible_window():
    assert 'def _media_reuse_needs_visible_restart(wants_video):' in LK
    assert 'presentation class from audio/headless to visible video' in LK
    assert 'if not _media_reuse_needs_visible_restart(stream_video):' in LK
    assert 'if stream_video: cmd.extend(["--video=yes","--force-window=yes"])' in LK

def test_queue_path_uses_same_presentation_transition_rule():
    assert 'if not _media_reuse_needs_visible_restart(queue_video):' in LK
