from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
LK=(ROOT/"look"/"lk").read_text(encoding="utf-8")

def test_fresh_mpv_launch_requires_readiness_before_success_session():
    assert "def _media_wait_for_mpv_start(proc, timeout=1.6):" in LK
    launch=LK.index("def _media_launch_session(session):")
    stream=LK.index("def _media_launch_stream(",launch)
    body=LK[launch:stream]
    assert "if not _media_wait_for_mpv_start(proc):" in body
    wait=body.index("if not _media_wait_for_mpv_start(proc):")
    assert wait < body.index('session["state"]="playing"',wait)

def test_video_window_is_immediate_on_queue_and_stream_launch():
    assert LK.count('cmd.extend(["--video=yes","--force-window=immediate"])') >= 2
    assert '"--force-window=yes"' not in LK

def test_start_failure_surfaces_owned_mpv_log():
    helper=LK[LK.index("def _media_wait_for_mpv_start"):LK.index("def _media_time",LK.index("def _media_wait_for_mpv_start"))]
    assert "mpv exited during startup" in helper
    assert "_media_tail_player_log(6)" in helper
