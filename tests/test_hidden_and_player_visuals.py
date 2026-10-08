import importlib.machinery
import importlib.util
import io
import os
from pathlib import Path
import subprocess
import sys
from unittest.mock import Mock

import pytest
from look import look_renderer as renderer, player_visuals

ROOT=Path(__file__).resolve().parents[1]


def test_cli_default_hidden_opt_in_and_legacy_opt_out(tmp_path):
    (tmp_path/'visible.txt').write_text('hello')
    (tmp_path/'.secret.txt').write_text('secret')
    def run(*args):
        return subprocess.check_output([sys.executable,str(ROOT/'look/lk'),*args],cwd=tmp_path,text=True)
    assert '.secret.txt' not in run()
    assert '.secret.txt' not in run(str(tmp_path))
    assert '.secret.txt' in run('--hidden')
    assert '.secret.txt' in run('hidden')  # lh uses this entry point
    assert '.secret.txt' not in run('--no-hidden')


def test_recursive_catalog_hides_hidden_ancestors_but_not_search_root(tmp_path):
    root=tmp_path/'.workspace'
    paths=[root/'notes.txt', root/'.secret'/'notes.txt', root/'visible'/'.notes.txt']
    assert renderer._catalog_matches(paths,'notes',False,root)==paths[:1]
    assert renderer._catalog_matches(paths,'notes',True,root)==paths


class Terminal(io.StringIO):
    def isatty(self): return True


def terminal(monkeypatch, module):
    monkeypatch.setattr(module.sys,'stdin',Mock(isatty=lambda:True,fileno=lambda:0))
    monkeypatch.setattr(module.sys,'stdout',Terminal())
    monkeypatch.setattr(module.termios,'tcgetattr',lambda fd:[])
    monkeypatch.setattr(module.termios,'tcsetattr',lambda *args:None)
    monkeypatch.setattr(module.tty,'setcbreak',lambda fd:None)


def test_shift_h_preserves_filter_query_and_refreshes_candidates(tmp_path,monkeypatch):
    terminal(monkeypatch,renderer)
    monkeypatch.setattr(renderer,'NativePreviewController',Mock)
    keys=iter(['H','Q']); monkeypatch.setattr(renderer,'read_key',lambda **kw:next(keys))
    paths=[tmp_path/'notes',tmp_path/'.notes']
    for p in paths: p.mkdir()
    hidden=False; queries=[]
    def toggle():
        nonlocal hidden
        hidden=not hidden
        return 'hidden shown'
    def candidates(query):
        queries.append((query,hidden))
        return paths if hidden else paths[:1]
    renderer.pager(['rows'],24,80,rebuild=lambda *args:['rows'],candidates=candidates,
                   on_hidden=toggle,force_interactive=True,initial_query='notes')
    assert hidden
    assert ('notes',False) in queries and ('notes',True) in queries
    assert not any(query!='notes' for query,_ in queries)


@pytest.mark.parametrize('mode',range(1,7))
def test_ambient_frames_animate_stay_bounded_and_pause(mode):
    for width,height in [(1,1),(18,7),(120,35)]:
        a=player_visuals.frame(mode,width,height,1.3)
        assert len(a)==height and all(len(row)==width for row in a)
    assert player_visuals.frame(mode,80,24,1.3)!=player_visuals.frame(mode,80,24,3.7)
    assert player_visuals.frame(mode,80,24,1.3,False)==player_visuals.frame(mode,80,24,3.7,False)


@pytest.fixture
def lk():
    loader=importlib.machinery.SourceFileLoader('lk_visual_test',str(ROOT/'look/lk'))
    spec=importlib.util.spec_from_loader(loader.name,loader)
    module=importlib.util.module_from_spec(spec); loader.exec_module(module)
    return module


def test_player_cycles_all_views_without_losing_transport_controls(lk,monkeypatch):
    terminal(monkeypatch,lk)
    modes=[]; calls=[]
    monkeypatch.setattr(lk,'_media_player_render',lambda mode=0:modes.append(mode) or 'frame')
    keys=iter(['v']*7+[' ','n','p','left','right','s','r','x','q'])
    monkeypatch.setattr(lk,'_read_tty_key',lambda *args:next(keys))
    monkeypatch.setattr(lk,'_media_control_session',lambda action:calls.append(action))
    monkeypatch.setattr(lk,'_media_mpv_request',lambda args:calls.append(args))
    monkeypatch.setattr(lk,'_media_shuffle_command',lambda:calls.append('shuffle'))
    monkeypatch.setattr(lk,'_media_repeat_command',lambda args:calls.append('repeat'))
    assert lk.media_player()==0
    assert modes[:8]==list(range(7))+[0]
    assert calls==['toggle','next','prev',['seek',-10,'relative'],['seek',10,'relative'],'shuffle','repeat','stop']


def test_full_visual_keeps_metadata_within_terminal(lk,monkeypatch):
    snap={'entry':{'artist':'Artist','title':'Song'},'state':'playing','position':30,'duration':60,
          'index':0,'session':{'queue':[{}]}}
    for columns,lines in [(20,10),(120,40)]:
        monkeypatch.setattr(lk.shutil,'get_terminal_size',lambda fallback:os.terminal_size((columns,lines)))
        rendered=lk._media_player_full_visual(snap,1)
        rows=rendered.splitlines()
        assert len(rows)<=lines-1
        assert all(len(lk._strip_ansi(row))<=columns-1 for row in rows)
    assert 'ambient animation' in rendered and 'Queue 1/1' in rendered


def test_lh_migrates_owned_home_shortcut_but_preserves_user_function():
    import shutil
    zsh=shutil.which('zsh')
    if not zsh: pytest.skip('zsh unavailable')
    source=(ROOT/'look/zshrc').read_text()
    def function(name):
        start=source.index(name+'() {')
        return source[start:source.index('\n}',start)+2]
    start=source.index("# Migrate only LOOK's old home shortcut")
    end=source.index("_look_short_install lh '_look hidden'",start)+len("_look_short_install lh '_look hidden'")
    setup='_LOOK_SHORTCUT_POLICY=respect\n_look() { print -r -- "$@"; }\n'
    setup+=function('_look_short_name_kind')+'\n'+function('_look_short_install')+'\n'
    for old,expected in [('lh() { _look home "$@"; }','hidden /tmp'),('lh() { print custom; }','custom')]:
        output=subprocess.check_output([zsh,'-f','-c',setup+old+'\n'+source[start:end]+'\nlh /tmp'],text=True).strip()
        assert output==expected
