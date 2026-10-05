from pathlib import Path
import contextlib
import io
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'look'))
import games
import lo_engine


def test_shared_router_classifies_games_and_current_news():
    assert lo_engine.route_intent('Gtnw') == 'games'
    assert lo_engine.route_intent('play a game') == 'games'
    assert lo_engine.route_intent('play chess') == 'games'
    assert lo_engine.route_intent('give me the headlines') == 'web_current'
    assert lo_engine.route_intent("what's the latest news?") == 'web_current'


def test_bare_games_preserves_hidden_easter_egg():
    out=io.StringIO()
    with contextlib.redirect_stdout(out):
        assert games.run([]) == 0
    assert out.getvalue().strip() == 'No games installed.'


def test_explicit_mode_remains_shortcut(monkeypatch):
    seen={}
    monkeypatch.setattr(games,'play_chess',lambda mode: seen.setdefault('mode',mode) or 0)
    assert games.run(['chess','0p']) == '0p' or seen.get('mode') == '0p'
    assert seen['mode'] == '0p'


def test_named_game_uses_wopr_selector_then_player_choice(monkeypatch):
    # Avoid a real TTY while checking the dispatch contract.
    class FakeTerminal:
        def __enter__(self): return 99
        def __exit__(self,*args): return False
    seen={}
    monkeypatch.setattr(games,'terminal',lambda: FakeTerminal())
    monkeypatch.setattr(games,'provision_login',lambda fd: True)
    monkeypatch.setattr(games,'launcher',lambda fd,preselected='': seen.setdefault('preselected',preselected) or preselected)
    monkeypatch.setattr(games,'choose_mode',lambda fd,game,default='1p': seen.setdefault('game',game) or '2p')
    monkeypatch.setattr(games,'play_checkers',lambda mode: seen.setdefault('mode',mode) or 0)
    games.run(['checkers'])
    assert seen['preselected']=='checkers'
    assert seen['game']=='checkers'


def test_albert_defers_search_and_game_intent_to_shared_router():
    server=(ROOT/'albert'/'server.py').read_text()
    assert 'force_search=False' in server
    assert 'shared_intent=_load_lo_engine().route_intent(q)' in server
    assert 'shared_intent!="games"' in server
