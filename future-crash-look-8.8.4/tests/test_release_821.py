from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'look'))
import games


def test_media_find_info_is_full_provenance_panel():
    src=(ROOT/'look'/'lk').read_text()
    assert 'MEDIA INFO' in src
    for field in ('Media ID','Root','Path','Identity','Available'):
        assert field in src
    assert 'info_mode=not info_mode' in src


def test_removable_watcher_publishes_visible_state():
    src=(ROOT/'look'/'media_watch.py').read_text()
    assert 'media_watch.json' in src
    assert "state='scanning'" in src and "state='indexed'" in src
    lk=(ROOT/'look'/'lk').read_text()
    assert 'removable {label' in lk


def test_bare_games_success_enters_real_launcher():
    src=(ROOT/'look'/'games.py').read_text()
    bare=src[src.index('if not args:'):src.index('game=aliases.get')]
    assert 'game=launcher(fd)' in bare
    assert '_dispatch(game,mode,gtnw_runner)' in bare
    assert 'NO GAMES INSTALLED' not in bare


def test_chess_and_checkers_are_visibly_larger():
    import io, contextlib
    for fn,board in ((games.render_chess,games.chess_initial()),(games.render_checkers,games.checkers_initial())):
        out=io.StringIO()
        with contextlib.redirect_stdout(out): fn(board,'1p','W')
        text=out.getvalue()
        assert 'a      b      c      d      e      f      g      h' in text
        assert len(text.splitlines()) >= 22


def test_dash_adds_media_and_tiny_signal_without_replacing_dash():
    src=(ROOT/'core'/'node.py').read_text()
    assert 'def _dash_media_status' in src
    assert 'MEDIA / SIGNAL' in src
    assert 'def _dash_signal' in src
    assert 'def _dash_render_mini' in src and 'def _dash_render_wide' in src
