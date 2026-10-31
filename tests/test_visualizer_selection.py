import io
import json
import os
from pathlib import Path
from unittest.mock import Mock
import pytest
import player_visuals as visuals
import visualizer_settings as settings
from test_media_request_regressions import lk


@pytest.fixture
def home(tmp_path,monkeypatch):
    monkeypatch.setattr(Path,'home',lambda:tmp_path)
    settings.enabled_modes(refresh=True)
    return tmp_path


def terminal(lk,monkeypatch,size=(70,25)):
    monkeypatch.setattr(lk.sys,'stdin',Mock(isatty=lambda:True,fileno=lambda:0))
    monkeypatch.setattr(lk.sys,'stdout',io.StringIO())
    monkeypatch.setattr(lk.sys.stdout,'isatty',lambda:True)
    monkeypatch.setattr(settings.termios,'tcgetattr',lambda fd:[])
    monkeypatch.setattr(settings.termios,'tcsetattr',lambda *args:None)
    monkeypatch.setattr(settings.tty,'setcbreak',lambda fd:None)
    monkeypatch.setattr(lk.shutil,'get_terminal_size',lambda *args:os.terminal_size(size))


def keys(lk,monkeypatch,values):
    values=iter(values);monkeypatch.setattr(lk,'_read_tty_key',lambda *args:next(values))


def test_fresh_default_is_all_enabled_and_does_not_create_config(home):
    assert settings.enabled_modes(refresh=True)==tuple(range(1,visuals.CYCLE_MODE))
    assert not settings.path().exists()


def test_disabled_names_persist_and_new_modes_stay_enabled(home,monkeypatch):
    settings.save({'Bars','Future visual'})
    assert 1 not in settings.enabled_modes()
    assert visuals.NAMES.index('Haunted Hollow')+1 in settings.enabled_modes()
    value=json.loads(settings.path().read_text());value['future_field']='keep'
    settings.path().write_text(json.dumps(value));settings.save({'Bars','Future visual','Waves'})
    assert json.loads(settings.path().read_text())['future_field']=='keep'
    assert 'Future visual' in settings.read()['disabled']


def test_manual_and_timed_cycles_share_selection_including_none():
    allowed=(7,23)
    assert visuals.playback_modes(allowed)==(0,7,23,visuals.CYCLE_MODE)
    assert [visuals.active_mode(visuals.CYCLE_MODE,t,allowed) for t in (0,9.99,10,19.99,20)]==[7,7,23,23,7]
    sequence=[];mode=0
    for _ in range(4):mode=visuals.next_mode(mode,allowed);sequence.append(mode)
    assert sequence==[7,23,visuals.CYCLE_MODE,0]
    assert visuals.available_mode(1,allowed)==7
    assert visuals.next_mode(0,())==0 and visuals.active_mode(visuals.CYCLE_MODE,100,())==0
    assert visuals.available_mode(visuals.CYCLE_MODE,())==0


def test_bad_config_falls_back_and_can_be_repaired_explicitly(home):
    settings.path().parent.mkdir(parents=True);settings.path().write_text('{bad json')
    assert settings.enabled_modes(refresh=True)==tuple(range(1,visuals.CYCLE_MODE))
    assert 'unreadable' in settings.warning()
    settings.save({'Bars'})
    assert settings.read()['disabled']==['Bars'] and not settings.warning()


def test_settings_reads_are_not_per_frame_and_other_panes_refresh(home,monkeypatch):
    clock=[100.];monkeypatch.setattr(settings.time,'monotonic',lambda:clock[0])
    original=settings.read;read=Mock(side_effect=original);monkeypatch.setattr(settings,'read',read)
    settings.enabled_modes(refresh=True)
    for _ in range(30):settings.enabled_modes()
    assert read.call_count==1
    settings.path().parent.mkdir(parents=True);settings.path().write_text(json.dumps({'schema':1,'disabled':['Bars']}))
    clock[0]+=1.1
    assert 1 not in settings.enabled_modes() and read.call_count==2


@pytest.mark.parametrize('size',[(30,12),(70,25),(150,40)])
def test_checklist_save_and_cancel_are_paged_and_bounded(home,lk,monkeypatch,size):
    terminal(lk,monkeypatch,size);frames=[]
    monkeypatch.setattr(lk,'_terminal_frame_payload',lambda text:frames.append(lk._strip_ansi(text)) or '')
    keys(lk,monkeypatch,[' ','esc'])
    assert not settings.picker(lk) and not settings.path().exists()
    keys(lk,monkeypatch,[' ','shiftright',' ','enter'])
    assert settings.picker(lk)
    assert settings.read()['disabled']==['Bars','Haunted Hollow']
    assert all(len(frame.splitlines())<=size[1] for frame in frames)
    assert any('Haunted Hollow' in frame for frame in frames)


def test_none_and_all_can_be_saved_without_breaking_normal_view(home,lk,monkeypatch):
    terminal(lk,monkeypatch)
    keys(lk,monkeypatch,['n','enter']);assert settings.picker(lk)
    assert settings.enabled_modes()==()
    keys(lk,monkeypatch,['a','enter']);assert settings.picker(lk)
    assert len(settings.enabled_modes())==visuals.CYCLE_MODE-1


def test_player_V_picker_preserves_transport_and_skips_disabled(home,lk,monkeypatch):
    terminal(lk,monkeypatch)
    frames=[];calls=[]
    monkeypatch.setattr(lk,'_media_player_render',lambda mode=0,visual_elapsed=0:frames.append(mode) or 'frame')
    def picker(*args):settings.save(set(visuals.NAMES[:-1]) - {'Album Art'});return True
    monkeypatch.setattr(lk.visualizer_settings,'picker',picker)
    monkeypatch.setattr(lk,'_media_control_session',lambda value:calls.append(value))
    keys(lk,monkeypatch,['V','v',' ','v','v','q'])
    assert lk.media_player()==0
    assert frames==[0,0,7,7,visuals.CYCLE_MODE,0]
    assert calls==['toggle']


@pytest.mark.parametrize('size',[(1,1),(20,6),(100,30),(240,80)])
def test_halloween_is_bounded_deterministic_paused_and_in_rotation(size):
    mode=visuals.NAMES.index('Haunted Hollow')+1;width,height=size
    frame=visuals.frame(mode,width,height,1,True,7)
    assert len(frame)==height and all(len(row)==width for row in frame)
    assert all(ord(char)<128 for row in frame for char in row)
    assert frame==visuals.frame(mode,width,height,1,True,7)
    assert visuals.frame(mode,width,height,1,False,7)==visuals.frame(mode,width,height,9,False,7)
    assert mode in {visuals.active_mode(visuals.CYCLE_MODE,n*10) for n in range(visuals.CYCLE_MODE-1)}
    if width>=20 and height>=10:assert frame!=visuals.frame(mode,width,height,5,True,7)


def test_cancelled_picker_does_not_advance_cycle_time(home,lk,monkeypatch):
    terminal(lk,monkeypatch)
    clock=[100.];frames=[]
    monkeypatch.setattr(lk.time,'monotonic',lambda:clock[0])
    monkeypatch.setattr(lk,'_media_player_render',lambda mode=0,visual_elapsed=0:frames.append((mode,visual_elapsed)) or 'frame')
    def picker(*args):clock[0]=150.;return False
    monkeypatch.setattr(lk.visualizer_settings,'picker',picker)
    events=iter([('V',110.),('q',150.)])
    def read(*args):key,clock[0]=next(events);return key
    monkeypatch.setattr(lk,'_read_tty_key',read)
    assert lk.media_player(initial_visualizer=visuals.CYCLE_MODE)==0
    assert frames==[(visuals.CYCLE_MODE,0.),(visuals.CYCLE_MODE,10.)]
