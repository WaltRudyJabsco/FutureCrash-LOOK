from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
LK=(ROOT/'look/lk').read_text()


def test_lk_mp_is_integrated_surface_not_second_backend():
    assert 'def media_mp(initial_query=""):' in LK
    assert 'library_rows,catalog_meta=_media_catalog_entries()' in LK
    assert '_media_cover_lines(chosen,right_w,art_h,background_remote=True)' in LK
    assert '_media_launch_session(media_core.new_session(picked))' in LK
    assert '_media_queue_append(picked)' in LK
    assert '_media_control_session("toggle")' in LK
    assert '_media_shuffle_command()' in LK
    assert '_media_repeat_command([])' in LK


def test_lk_mp_is_reachable_both_ways():
    assert 'if cmd=="mp": return media_mp(" ".join(rest))' in LK
    assert 'if raw=="mp": return media_mp(" ".join(args[1:]))' in LK


def test_lk_mp_controls_are_documented_in_surface():
    for text in ('A add queue','L library','Q queue','s shuffle','r repeat','/ search'):
        assert text in LK


def test_media_mp_initializes_search_state_before_first_frame():
    body=LK.split('def media_mp(initial_query=""):',1)[1].split('def _media_outputs_command():',1)[0]
    init=body.split('def row_id(row):',1)[0]
    assert 'search_mode=False' in init
    assert 'search_before=query' in init
    assert init.index('search_mode=False') < body.index('if search_mode:')
