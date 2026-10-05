from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
NODE=(ROOT/'core/node.py').read_text()
LK=(ROOT/'look/lk').read_text()


def test_daemon_media_helpers_find_package_manager_bins():
    block=NODE[NODE.index('def _service_media_tool'):NODE.index('def _identify_media_entry')]
    assert '/home/linuxbrew/.linuxbrew/bin' in block
    assert '/opt/homebrew/bin' in block
    assert 'ffmpeg=_service_media_tool("ffmpeg")' in block
    assert 'chafa=_service_media_tool("chafa")' in block


def test_remote_preview_inherits_working_playback_route():
    block=LK[LK.index('def _media_remote_preview_identity'):LK.index('def _media_remote_preview_key')]
    assert 'source=_media_entry_source(row)' in block
    assert 'parsed.path=="/v1/media/item"' in block
    assert 'q.get("node")' in block and 'q.get("id")' in block


def test_media_find_swaps_complete_frames_without_blank_clear_cycle():
    block=LK[LK.index('def _media_selector('):LK.index('def _media_selector_finish')]
    assert 'frame_io=io.StringIO()' in block
    assert 'with redirect_stdout(frame_io):' in block
    assert 'sys.stdout.write(_terminal_frame_payload(frame))' in block
    # One initial clear is fine; navigation frames must not clear to blank first.
    assert block.count('sys.stdout.write("\\033[2J\\033[H")') == 0


def test_player_s_toggles_real_mpv_shuffle():
    helper=LK[LK.index('def _media_shuffle_command'):LK.index('def _media_repeat_command')]
    player=LK[LK.index('def media_player'):LK.index('def _media_outputs_command')]
    assert '"playlist-shuffle" if enabled else "playlist-unshuffle"' in helper
    assert 'session["runtime_queue_indices"]=mapping' in helper
    assert 'elif key=="s": _media_shuffle_command()' in player
    assert 's shuffle' in LK[LK.index('def _media_player_render'):LK.index('def media_player')]
