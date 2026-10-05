from pathlib import Path
import importlib.machinery, importlib.util, sys

ROOT=Path(__file__).resolve().parents[1]
loader=importlib.machinery.SourceFileLoader('look_lk_701',str(ROOT/'look'/'lk'))
spec=importlib.util.spec_from_loader(loader.name,loader)
lk=importlib.util.module_from_spec(spec); sys.modules[loader.name]=lk; loader.exec_module(lk)


def test_power_auto_runs_ordinary_commands_without_confirmation(tmp_path, monkeypatch):
    monkeypatch.setattr(lk,'_confirm_command',lambda command: (_ for _ in ()).throw(AssertionError('ordinary command prompted')))
    monkeypatch.setattr(lk.shutil,'which',lambda name: '/bin/bash' if name=='zsh' else None)
    result=lk._run_command_tool(tmp_path,{'command':'printf power-ok'},'power')
    assert result == 'exit 0\npower-ok'


def test_power_keeps_hazardous_command_at_native_gate(tmp_path, monkeypatch):
    monkeypatch.setattr(lk,'_confirm_command',lambda command: False)
    assert lk._power_command_risk('rm -rf doomed') == 'hazardous'
    assert lk._run_command_tool(tmp_path,{'command':'rm -rf doomed'},'power') == 'Command denied by user.'


def test_four_profiles_have_distinct_filesystem_authority(tmp_path, monkeypatch):
    home=tmp_path/'home'; home.mkdir()
    other=home/'Documents'; other.mkdir()
    work=home/'project'; work.mkdir()
    monkeypatch.setattr(lk,'HOME',home)

    lk._FILESYSTEM_ACCESS_PROFILE='conservative'
    assert lk._path_access_allowed(work,work/'x','read')
    assert not lk._path_access_allowed(work,other/'x','read')
    assert not lk._path_access_allowed(work,other/'x','write')

    lk._FILESYSTEM_ACCESS_PROFILE='workspace'
    assert lk._path_access_allowed(work,other/'x','read')
    assert lk._path_access_allowed(work,other/'x','write')

    lk._FILESYSTEM_ACCESS_PROFILE='power'
    assert lk._path_access_allowed(work,Path('/tmp')/'x','write')

    lk._FILESYSTEM_ACCESS_PROFILE='unsafe'
    assert lk._path_access_allowed(work,Path('/tmp')/'x','write')


def test_interactive_interrupt_is_successful_launch_receipt():
    typed=lk._command_result('interactive exit 130 · launched; terminal session interrupted by user')
    assert typed.ok
    assert typed.status == 'interrupted'


def test_explicit_command_retry_language_reuses_last_action():
    action={'tool':'run_command','args':{'command':'asciiquarium','interactive':True},'path':'asciiquarium'}
    assert lk._lo_repeat_intent('run it again')
    assert lk._lo_action_continuation('try it now i fixed something',action)
    assert lk._lo_action_continuation('run it again',action)


def test_command_attempt_is_retained_even_when_interrupted():
    action=lk._lo_action_from_tool('run_command',{'command':'asciiquarium','interactive':True},'interactive exit 130 · launched; terminal session interrupted by user')
    assert action['tool']=='run_command'
    assert action['args']['interactive'] is True
    assert action['path']=='asciiquarium'


def test_running_session_refreshes_persistent_access_profile_and_receipt_context():
    source=(ROOT/'look'/'lk').read_text()
    assert 'refreshed_profile=_load_lo_profile()' in source
    assert 'messages[capability_message_index]["content"]=capability_notes[profile]' in source
    assert 'LATEST AUTHORITATIVE HOST RECEIPT' in source
