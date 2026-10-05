from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LK = (ROOT / "look" / "lk").read_text(encoding="utf-8")

def test_current_mpv_video_launch_uses_automatic_track_selection():
    assert '"--video=yes"' not in LK
    assert LK.count('cmd.append("--force-window=immediate")') >= 2

def test_queue_and_fabric_stream_share_visible_video_rule():
    queue = LK[LK.index("def _media_launch_session"):LK.index("def _media_launch_stream")]
    stream = LK[LK.index("def _media_launch_stream"):LK.index("def _media_stream_command", LK.index("def _media_launch_stream"))]
    assert 'if queue_video:' in queue
    assert 'cmd.append("--force-window=immediate")' in queue
    assert 'if stream_video:' in stream
    assert 'cmd.append("--force-window=immediate")' in stream
