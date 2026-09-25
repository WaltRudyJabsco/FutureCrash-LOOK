from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'look'))
import games as g


def test_board_renderers_are_visually_structured(capsys):
    g.render_chess(g.chess_initial(),'1p','W')
    chess=capsys.readouterr().out
    assert g.BG_LIGHT in chess and g.BG_DARK in chess
    assert chess.count('a  b  c  d  e  f  g  h') == 2

    g.render_checkers(g.checkers_initial(),'1p','W')
    checkers=capsys.readouterr().out
    assert '●' in checkers
    assert g.BG_LIGHT in checkers and g.BG_DARK in checkers
    assert checkers.count('a  b  c  d  e  f  g  h') == 2

    g.render_bg(g.backgammon_initial(),'1p','W',[3,5])
    bg=capsys.readouterr().out
    assert '┌' in bg and '└' in bg and '│BAR│' in bg
    assert '○' in bg and '●' in bg
    assert 'OFF  WHITE:' in bg and 'DICE' in bg


def test_game_footer_and_menu_return_contract():
    assert 'q/esc menu' in g.footer('1p')
    assert g.MENU_RETURN != 0
    source=(ROOT/'look'/'games.py').read_text()
    assert 'if game=="gtnw" or result!=MENU_RETURN' in source
    assert 'if key=="s": return 0' in source


def test_wopr_login_is_ritual_not_remembered_state():
    source=(ROOT/'look'/'games.py').read_text()
    block=source[source.index('def provision_login'):source.index('def launcher')]
    assert '_provisioned()' not in block
    assert 'LOOK_GAMES_SKIP_LOGON' in block
    assert 'wopr_say("GREETINGS PROFESSOR FALKEN. SHALL WE PLAY A GAME?")' in block
    assert 'NO GAMES INSTALLED.' in source


def test_voice_dependencies_and_platform_adapters():
    source=(ROOT/'look'/'games.py').read_text()
    installer=(ROOT/'install-look.sh').read_text()
    assert '"espeak-ng"' in source and '"play"' in source
    assert '/v1/audio/speak' in source
    assert '"say"' in source  # graceful macOS fallback only
    assert 'mpv qrencode)' in installer and 'core+=(sox espeak-ng)' in installer
    assert 'core+=(sox espeak-ng)' in installer
