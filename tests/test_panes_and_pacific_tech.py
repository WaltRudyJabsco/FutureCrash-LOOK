import io
import os
from pathlib import Path
import sys
from types import SimpleNamespace
from unittest.mock import Mock
import pytest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'look'))
import real_genius as genius
from look import terminal_style as style, player_visuals, look_renderer as renderer


def test_kitty_pane_targets_original_tab_and_quotes_directory_as_one_argument(tmp_path,monkeypatch):
    path=tmp_path/'writing project';path.mkdir()
    monkeypatch.delenv('TMUX',raising=False);monkeypatch.setenv('KITTY_WINDOW_ID','42')
    monkeypatch.setattr(style.shutil,'which',lambda name:'/bin/'+name)
    run=Mock(return_value=SimpleNamespace(returncode=0));monkeypatch.setattr(style.subprocess,'run',run)
    result=style.open_pane(path)
    assert result.startswith('Shell opened beside LOOK') and 'switch pane' in result and 'Ctrl-Shift-W close focused pane' in result
    first,second=[call.args[0] for call in run.call_args_list]
    assert first[-3:]==['--match','window_id:42','splits']
    assert '--source-window' in second and '--next-to' in second
    assert second[-2:]==['--cwd',str(path)]
    assert second[second.index('--match')+1]=='window_id:42'
    assert not any('shell' in call.kwargs for call in run.call_args_list)


def test_tmux_pane_and_unsupported_terminal(tmp_path,monkeypatch):
    monkeypatch.setenv('TMUX','session');monkeypatch.setattr(style.shutil,'which',lambda name:'/bin/tmux')
    run=Mock(return_value=SimpleNamespace(returncode=0));monkeypatch.setattr(style.subprocess,'run',run)
    style.open_pane(tmp_path)
    assert run.call_args.args[0]==['tmux','split-window','-h','-c',str(tmp_path)]
    monkeypatch.delenv('TMUX');monkeypatch.delenv('KITTY_WINDOW_ID',raising=False);run.reset_mock()
    assert 'LOOK still works' in style.open_pane(tmp_path)
    run.assert_not_called()


def test_refused_pane_does_not_launch_shell(tmp_path,monkeypatch):
    monkeypatch.delenv('TMUX',raising=False);monkeypatch.setenv('KITTY_WINDOW_ID','42')
    monkeypatch.setattr(style.shutil,'which',lambda name:'/bin/'+name)
    run=Mock(return_value=SimpleNamespace(returncode=1));monkeypatch.setattr(style.subprocess,'run',run)
    assert 'fully restart Kitty' in style.open_pane(tmp_path)
    assert run.call_count==1


def test_w_remains_filter_text_then_opens_from_browse(tmp_path,monkeypatch):
    from test_hidden_and_player_visuals import terminal
    terminal(monkeypatch,renderer);monkeypatch.setattr(renderer,'NativePreviewController',Mock)
    path=tmp_path/'aW';path.write_text('hello')
    keys=iter(['W','\x1b','W','Q']);monkeypatch.setattr(renderer,'read_key',lambda *args,**kw:next(keys))
    opened=[];queries=[]
    monkeypatch.setattr(renderer.terminal_style,'open_pane',lambda cwd:opened.append(cwd) or 'opened')
    def candidates(query):queries.append(query);return [path]
    renderer.pager(['aW'],24,80,force_interactive=True,current_dir=tmp_path,
                   initial_query='a',candidates=candidates,rebuild=lambda *args:['aW'],
                   browse_rebuild=lambda *args:['browse'])
    assert 'aW' in queries and opened==[tmp_path]


@pytest.mark.parametrize('platform,focus',[('darwin','Option-Shift-W'),('linux','Alt-Shift-W')])
def test_pane_shortcuts_match_terminal_and_platform(monkeypatch,platform,focus):
    monkeypatch.delenv('TMUX',raising=False);monkeypatch.setattr(style.sys,'platform',platform)
    assert style.pane_shortcuts()==[focus+' switch pane','Ctrl-Shift-W close focused pane']
    monkeypatch.setenv('TMUX','session')
    assert style.pane_shortcuts()==['Ctrl-B then O switch pane','exit closes shell pane']


def test_pane_help_persists_after_notice_and_in_filter(tmp_path,monkeypatch):
    from test_hidden_and_player_visuals import terminal
    terminal(monkeypatch,renderer);monkeypatch.setattr(renderer,'NativePreviewController',Mock)
    monkeypatch.delenv('TMUX',raising=False)
    path=tmp_path/'file.txt';path.write_text('text')
    keys=iter(['W','/','\x1b','Q']);monkeypatch.setattr(renderer,'read_key',lambda *args,**kwargs:next(keys))
    monkeypatch.setattr(style,'open_pane',lambda cwd:'Shell opened beside LOOK')
    footer=renderer.action_footer;frames=[]
    def capture(parts,width):
        frames.append(list(parts));return footer(parts,width)
    monkeypatch.setattr(renderer,'action_footer',capture)
    renderer.pager(['file.txt'],24,80,force_interactive=True,current_dir=tmp_path,
                   candidates=lambda query:[path],rebuild=lambda *args:['file.txt'],
                   browse_rebuild=lambda *args:['file.txt'])
    assert not any('switch pane' in part for part in frames[0])
    assert all('Ctrl-Shift-W close focused pane' in frame for frame in frames[1:])
    assert any('Esc clear' in frame and 'Ctrl-Shift-W close focused pane' in frame for frame in frames)


def test_pane_resize_reflows_browse_without_a_keypress(tmp_path,monkeypatch):
    from test_hidden_and_player_visuals import terminal
    terminal(monkeypatch,renderer);monkeypatch.setattr(renderer,'NativePreviewController',Mock)
    sizes=iter([os.terminal_size((40,24)),os.terminal_size((100,30))])
    monkeypatch.setattr(renderer.shutil,'get_terminal_size',lambda fallback:next(sizes))
    keys=iter([renderer.RESIZE_KEY,'Q'])
    monkeypatch.setattr(renderer,'read_key',lambda *args,**kwargs:next(keys))
    widths=[]
    def rebuild(picked=None,marked=None,width=None):
        widths.append(width);return [f'grid at {width}']
    renderer.pager(['rows'],24,80,force_interactive=True,browse_rebuild=rebuild,current_dir=tmp_path)
    assert widths==[None,40,100]


def test_resize_clamps_browse_page_after_wider_grid_has_fewer_rows(tmp_path,monkeypatch):
    from test_hidden_and_player_visuals import terminal
    terminal(monkeypatch,renderer);monkeypatch.setattr(renderer,'NativePreviewController',Mock)
    sizes=iter([os.terminal_size((40,24)),os.terminal_size((40,24)),os.terminal_size((100,30))])
    monkeypatch.setattr(renderer.shutil,'get_terminal_size',lambda fallback:next(sizes))
    keys=iter(['g',renderer.RESIZE_KEY,'Q'])
    monkeypatch.setattr(renderer,'read_key',lambda *args,**kwargs:next(keys))
    def rebuild(picked=None,marked=None,width=None):
        return ['wide grid row'] if width==100 else [f'narrow row {n}' for n in range(100)]
    renderer.pager(['rows'],24,40,force_interactive=True,browse_rebuild=rebuild,current_dir=tmp_path)
    assert 'wide grid row' in renderer.sys.stdout.getvalue()


def test_resize_wakes_blocked_input_and_preserves_pending_key(monkeypatch):
    import signal
    keyboard=os.pipe();real_select=renderer.select.select;raised=False
    monkeypatch.setattr(renderer.sys,'stdin',Mock(fileno=lambda:keyboard[0]))
    monkeypatch.setattr(renderer.termios,'tcgetattr',lambda fd:[])
    monkeypatch.setattr(renderer.termios,'tcsetattr',lambda *args:None)
    monkeypatch.setattr(renderer.tty,'setcbreak',lambda *args:None)
    monkeypatch.setattr(renderer.shutil,'get_terminal_size',lambda fallback:os.terminal_size((80,24)))
    previous=signal.getsignal(signal.SIGWINCH)
    def select_once(*args):
        nonlocal raised
        if not raised:raised=True;signal.raise_signal(signal.SIGWINCH)
        return real_select(*args)
    monkeypatch.setattr(renderer.select,'select',select_once)
    try:
        os.write(keyboard[1],b'q')
        assert renderer.read_key(timeout=1,expected_size=(80,24))==renderer.RESIZE_KEY
        assert signal.getsignal(signal.SIGWINCH)==previous
        assert renderer.read_key(timeout=0)=='q'
    finally:
        for pipe in keyboard:os.close(pipe)


@pytest.mark.parametrize('scene',genius.SCENES)
@pytest.mark.parametrize('size',[(1,1),(24,8),(80,24),(180,50)])
def test_scenes_are_bounded_deterministic_and_animate(scene,size):
    for age in (0,5,13,23,10000):
        rows=genius.frame(scene,*size,age)
        assert len(rows)==size[1] and all(len(row)==size[0] for row in rows)
        assert rows==genius.frame(scene,*size,age)
        assert all('\x1b' not in row for row in rows)
    if scene!='genius' and size==(80,24):
        assert genius.frame(scene,*size,0)!=genius.frame(scene,*size,13)


def test_scene_commands_are_plain_and_finish_when_redirected(monkeypatch):
    output=io.StringIO();monkeypatch.setattr(genius.sys,'stdout',output)
    for scene in genius.SCENES:assert genius.run(scene)==0
    assert '\x1b' not in output.getvalue() and 'PACIFIC TECH' in output.getvalue()


def test_moon_jelly_pauses_and_joins_rotation():
    mode=player_visuals.NAMES.index('Moon Jelly')+1
    assert player_visuals.active_mode(player_visuals.CYCLE_MODE,100)==mode
    assert player_visuals.active_mode(player_visuals.CYCLE_MODE,(player_visuals.CYCLE_MODE-1)*player_visuals.CYCLE_INTERVAL_SECONDS)==1
    assert player_visuals.frame(mode,80,24,0)!=player_visuals.frame(mode,80,24,2)
    assert player_visuals.frame(mode,80,24,0,False)==player_visuals.frame(mode,80,24,2,False)


def test_pane_bindings_survive_profile_reset_and_control_is_scoped():
    text=(ROOT/'terminal/kitty.conf').read_text()
    after=text.split('clear_all_shortcuts yes',1)[1]
    assert 'map alt+shift+w next_window' in after
    assert 'map ctrl+shift+enter combine : goto_layout splits : launch' in after
    assert 'remote_control_password look-panes launch goto-layout' in text
    assert 'allow_remote_control yes' not in text and 'listen_on ' not in text

@pytest.mark.parametrize('pixels,expected',[((1200,600),True),((500,900),False),((600,600),True)])
def test_split_uses_physical_active_pane_geometry(pixels,expected,monkeypatch):
    import fcntl,struct
    monkeypatch.setattr(fcntl,'ioctl',lambda *a:struct.pack('HHHH',30,100,*pixels))
    monkeypatch.setattr(style.sys,'stdout',SimpleNamespace(fileno=lambda:1))
    assert style.pane_is_wide()==expected


def test_tmux_splits_tall_active_pane_vertically(tmp_path,monkeypatch):
    monkeypatch.setenv('TMUX','session');monkeypatch.setattr(style.shutil,'which',lambda name:'/bin/tmux')
    run=Mock(side_effect=[SimpleNamespace(returncode=0,stdout='40 60 8 16'),SimpleNamespace(returncode=0)])
    monkeypatch.setattr(style.subprocess,'run',run)
    assert style.open_pane(tmp_path).startswith('Shell opened')
    assert run.call_args.args[0]==['tmux','split-window','-v','-c',str(tmp_path)]
