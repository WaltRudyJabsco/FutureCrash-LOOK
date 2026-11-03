import io
import json
import os
from pathlib import Path
import subprocess
import sys
from unittest.mock import Mock

import pytest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'look'))
import saver


@pytest.fixture
def settings_file(tmp_path,monkeypatch):
    target=tmp_path/'saver.json';monkeypatch.setattr(saver,'settings_path',lambda:target)
    return target


def test_fresh_defaults_and_atomic_settings_roundtrip(settings_file):
    value=saver.load()
    assert value['display']=='all' and value['scene']=='cycle'
    assert value['independent'] and value['inversions']
    assert 'Album Art' not in value['enabled']
    value.update(scene='Dune Sea',palette='mercury',interval=30)
    saver.save(value)
    assert saver.load()==value


@pytest.mark.parametrize('key,value',[('interval',0),('interval',float('nan')),('interval',True),('display','elsewhere'),('enabled',['unknown']),('palette','bad'),('independent','yes'),('schema',99)])
def test_invalid_preferences_are_rejected(key,value):
    with pytest.raises(ValueError):saver.validate({**saver.defaults(),key:value})


def test_bad_settings_are_not_silently_overwritten(settings_file):
    settings_file.write_text('{broken')
    assert saver.main(['--save'],quick=True)==1
    assert settings_file.read_text()=='{broken'


def test_scene_aliases_and_empty_cycle():
    assert saver.scene_name('dune-sea')=='Dune Sea'
    with pytest.raises(ValueError):saver.SceneRun({**saver.defaults(),'enabled':[]},1)
    assert saver.SceneRun({**saver.defaults(),'scene':'Stars','enabled':[]},1).scenes==['Stars']


def test_matching_displays_stay_matching_even_after_missed_frames():
    config={**saver.defaults(),'independent':False}
    one=saver.SceneRun(config,42);two=saver.SceneRun(config,42)
    one.sample(0,80,30);one.sample(25,80,30)
    assert one.sample(65,80,30)==two.sample(65,80,30)
    assert one.sample(65.1,80,30)[2]==one.sample(65,80,30)[2]


def test_independent_runs_have_variation_and_bounded_frames():
    one=saver.SceneRun(saver.defaults(),1);two=saver.SceneRun(saver.defaults(),2)
    assert one.sample(5,80,30)!=two.sample(5,80,30)
    for name in saver.SCENES:
        run=saver.SceneRun({**saver.defaults(),'scene':name},3)
        scene,lines,(paper,ink)=run.sample(2,40,12)
        assert scene==name and len(lines)==12
        assert all(len(line)==40 for line in lines)
        assert saver.terminal_style.contrast(paper,ink)>=4.5


def test_command_line_overrides_do_not_save_without_save(settings_file,monkeypatch):
    launch=Mock(return_value=0);monkeypatch.setattr(saver,'launch',launch)
    assert saver.main(['Dune Sea','--display','current','--matching','--no-invert'],quick=True)==0
    value=launch.call_args.args[0]
    assert value['scene']=='Dune Sea' and value['display']=='current'
    assert not value['independent'] and not value['inversions']
    assert not settings_file.exists()
    assert saver.main(['start','Stars','--preview'])==0
    assert launch.call_args.args[0]['scene']=='Stars'
    assert launch.call_args.kwargs['preview']


def test_save_does_not_launch(settings_file,monkeypatch):
    launch=Mock();monkeypatch.setattr(saver,'launch',launch)
    assert saver.main(['--palette','mercury','--save'],quick=True)==0
    launch.assert_not_called()
    assert saver.load()['palette']=='mercury'


def test_missing_runtime_has_actionable_error(monkeypatch):
    monkeypatch.setattr(saver,'interpreter',lambda:None)
    with pytest.raises(ValueError,match='lk saver setup'):saver.launch(saver.defaults())


def test_launch_keeps_names_as_json_not_shell_commands(monkeypatch):
    monkeypatch.setattr(saver,'interpreter',lambda:Path('/test/python'))
    monkeypatch.setenv('QT_QPA_PLATFORM','offscreen')
    call=Mock(return_value=Mock(returncode=0));monkeypatch.setattr(saver.subprocess,'run',call)
    assert saver.launch(saver.defaults(),preview=True,seconds=2)==0
    assert isinstance(call.call_args.args[0],list)
    assert not call.call_args.kwargs.get('shell')
    request=json.loads(call.call_args.kwargs['input'])
    assert request['preview'] and request['seconds']==2


def test_no_arguments_uses_picker_only_for_saver(settings_file,monkeypatch):
    picker=Mock(return_value=0);launch=Mock(return_value=0)
    monkeypatch.setattr(saver,'picker',picker);monkeypatch.setattr(saver,'launch',launch)
    ui=object()
    assert saver.main([],ui=ui)==0
    picker.assert_called_once_with(ui);launch.assert_not_called()
    assert saver.main([],ui=ui,quick=True)==0
    assert launch.call_count==1


def test_gui_without_qt_does_not_prevent_command_help():
    result=subprocess.run([sys.executable,str(ROOT/'look/lk'),'sv','--help'],capture_output=True,text=True)
    assert result.returncode==0 and '--display' in result.stdout


@pytest.mark.parametrize('size',[(80,24),(110,32)])
def test_picker_controls_save_preview_and_return(settings_file,monkeypatch,size):
    import importlib.machinery
    import importlib.util
    loader=importlib.machinery.SourceFileLoader('lk_saver_ui',str(ROOT/'look/lk'))
    spec=importlib.util.spec_from_loader(loader.name,loader)
    ui=importlib.util.module_from_spec(spec);loader.exec_module(ui)
    class Terminal(io.StringIO):
        def isatty(self):return True
        def fileno(self):return 0
    output=Terminal()
    monkeypatch.setattr(sys,'stdin',Terminal());monkeypatch.setattr(sys,'stdout',output)
    monkeypatch.setattr(saver.termios,'tcgetattr',lambda fd:[])
    monkeypatch.setattr(saver.termios,'tcsetattr',lambda *args:None)
    monkeypatch.setattr(saver.tty,'setcbreak',lambda fd:None)
    monkeypatch.setattr(ui.shutil,'get_terminal_size',lambda *_:os.terminal_size(size))
    keys=iter(['down',' ','D','M','I','+','C','A','P','enter','esc'])
    monkeypatch.setattr(ui,'_read_tty_key',lambda *_:next(keys))
    frames=[]
    monkeypatch.setattr(ui,'_terminal_frame_payload',lambda text:frames.append(text) or text)
    launch=Mock(return_value=0);monkeypatch.setattr(saver,'launch',launch)
    assert saver.picker(ui)==0
    value=saver.load()
    assert value['scene']=='Bars' and 'Bars' not in value['enabled']
    assert value['display']=='current' and not value['independent'] and not value['inversions']
    assert value['interval']==25 and value['palette']=='neon'
    assert [call.kwargs['preview'] for call in launch.call_args_list]==[True,False]
    for frame in frames:
        assert len(frame.splitlines())<=size[1]
        assert all(len(ui._strip_ansi(line))<=size[0] for line in frame.splitlines())
    assert '\033[?25h' in output.getvalue()


def test_live_colors_change_without_changing_scene_or_flickering():
    run=saver.SceneRun({**saver.defaults(),'scene':'Stars','palette':'harbor','inversions':False},42)
    before=run.sample(1,50,20)
    run.next_color()
    after=run.sample(1,50,20)
    assert before[:2]==after[:2] and before[2]!=after[2]
    assert after[2]==run.sample(1.1,50,20)[2]


def test_next_visual_works_from_named_scene_and_uses_enabled_list():
    run=saver.SceneRun({**saver.defaults(),'scene':'Stars','enabled':['Stars','Dune Sea'],'independent':False},42)
    assert run.sample(65,50,20)[0]=='Stars'
    run.next_scene()
    assert run.sample(65,50,20)[0]=='Dune Sea'
    run.next_scene()
    assert run.sample(65,50,20)[0]=='Stars'


def test_matching_controls_remain_synchronized():
    config={**saver.defaults(),'independent':False}
    one=saver.SceneRun(config,42);two=saver.SceneRun(config,42)
    for run in (one,two):
        run.sample(10,40,20);run.next_scene();run.next_color()
    assert one.sample(11,40,20)==two.sample(11,40,20)
