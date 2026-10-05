from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'look'))
import games as g


def test_modes_and_ttt_perfect_move():
    assert g.mode_from('0p')=='0p'
    assert g.mode_from('1')=='1p'
    assert g.mode_from('2p')=='2p'
    board=['X','X','','O','O','','','','']
    assert g.ttt_ai(board,'X')==2


def test_chess_initial_and_legal_moves():
    board=g.chess_initial()
    moves=g.chess_moves(board,'W')
    assert len(moves)==20
    e2=g.parse_sq('e2'); e4=g.parse_sq('e4')
    assert any(a==e2 and b==e4 for a,b,_ in moves)
    empty=['']*64; empty[g.parse_sq('e2')]='P'
    assert g.chess_attacked(empty,g.parse_sq('d3'),'W')
    assert not g.chess_attacked(empty,g.parse_sq('e3'),'W')


def test_checkers_initial_and_mandatory_capture():
    board=g.checkers_initial()
    assert sum(1 for p in board if p.lower()=='w')==12
    assert sum(1 for p in board if p.lower()=='b')==12
    b=['']*64
    b[g.parse_sq('c3')]='w'; b[g.parse_sq('d4')]='b'
    moves=g.checkers_moves(b,'W')
    assert len(moves)==1
    assert [g.coord(i) for i in moves[0][0]]==['c3','e5']


def test_backgammon_standard_setup_and_moves():
    bg=g.backgammon_initial()
    assert sum(max(0,x) for x in bg.points)==15
    assert sum(max(0,-x) for x in bg.points)==15
    assert 24 in g.bg_legal_sources(bg,'W',1)
    assert 1 in g.bg_legal_sources(bg,'B',1)


def test_dispatch_and_installer_contract():
    lk=(ROOT/'look'/'lk').read_text()
    installer=(ROOT/'install-look.sh').read_text()
    assert 'look_games.run(rest, gtnw_runner=game_gtnw)' in lk
    assert 'look/games.py' in installer
    assert 'lk games chess' in lk
