import importlib.machinery, importlib.util
import sys
import time
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
LOOK=ROOT/'look'/'lk'
loader=importlib.machinery.SourceFileLoader('look_lk_705',str(LOOK))
spec=importlib.util.spec_from_loader(loader.name,loader)
lk=importlib.util.module_from_spec(spec); sys.modules[loader.name]=lk; loader.exec_module(lk)


def test_jev_resolves_close_that_window_to_one_typed_terminal():
    ref={'id':'term_1','kind':'terminal_window','platform':'linux','pid_file':'/tmp/x.pid'}
    decision=lk._jev_module().referential_action('can you close that window',[ref])
    assert decision['action']=='close'
    assert decision['object']==ref


def test_jev_close_it_is_ambiguous_with_two_compatible_objects():
    refs=[
        {'id':'term_1','kind':'terminal_window','platform':'linux','pid_file':'/tmp/a.pid'},
        {'id':'term_2','kind':'terminal_window','platform':'linux','pid_file':'/tmp/b.pid'},
    ]
    assert lk._jev_module().referential_action('close it',refs) is None


def test_linux_new_terminal_records_inside_terminal_handle(tmp_path,monkeypatch):
    lk.STATE_DIR=tmp_path/'state'
    monkeypatch.setattr(lk.sys,'platform','linux')
    monkeypatch.setattr(lk.shutil,'which',lambda name: '/usr/bin/'+name if name in {'x-terminal-emulator','zsh'} else None)
    class P:
        pid=4321
    calls=[]
    monkeypatch.setattr(lk.subprocess,'Popen',lambda argv,**kw: calls.append((argv,kw)) or P())
    args={'command':'asciiquarium','new_terminal':True}
    result=lk._launch_command_new_terminal('asciiquarium',tmp_path,'/usr/bin/zsh',args)
    assert result.startswith('new terminal dispatch ok')
    ref=args['_referent']
    assert ref['kind']=='terminal_window' and ref['launcher_pid']==4321
    assert ref['pid_file'].endswith('.pid')
    # The command executed inside the new terminal writes its own PID before exec.
    assert "printf '%s\\n' $$" in calls[0][0][-1]
    assert 'asciiquarium' in calls[0][0][-1]


def test_close_linux_terminal_uses_recorded_inside_pid(tmp_path,monkeypatch):
    pid_file=tmp_path/'term.pid'; pid_file.write_text('2468\n')
    sent=[]
    monkeypatch.setattr(lk.os,'kill',lambda pid,sig: sent.append((pid,sig)))
    result=lk._close_typed_referent({'kind':'terminal_window','platform':'linux','pid_file':str(pid_file),'launcher_pid':999})
    assert result.startswith('close ok')
    assert sent==[(2468,lk.signal.SIGTERM)]


def test_close_macos_terminal_uses_window_id(monkeypatch):
    monkeypatch.setattr(lk.sys,'platform','darwin')
    class P:
        returncode=0; stdout=''
    calls=[]
    monkeypatch.setattr(lk.subprocess,'run',lambda argv,**kw: calls.append(argv) or P())
    result=lk._close_typed_referent({'kind':'terminal_window','platform':'darwin','os_window_id':'77'})
    assert result.startswith('close ok')
    assert 'id is 77' in calls[0][-1]


def test_recent_referent_comes_from_live_state_not_durable_receipt(monkeypatch):
    ref={'id':'term_1','kind':'terminal_window','platform':'linux','pid_file':'/tmp/x.pid'}
    monkeypatch.setattr(lk,'_live_state_referents',lambda:[ref])
    assert lk._lo_recent_referents(None)[0]==ref


def test_real_lo_turn_closes_recent_typed_terminal_before_cognition(tmp_path,monkeypatch,capsys):
    ref={'id':'term_1','kind':'terminal_window','platform':'linux','pid_file':str(tmp_path/'term.pid'),'launcher_pid':123,'command':'asciiquarium','status':'open'}
    prior={'tool':'run_command','path':'asciiquarium','args':{'command':'asciiquarium','new_terminal':True,'interactive':False,'_referent':ref}}
    monkeypatch.setattr(lk,'_lo_latest_command_action',lambda:prior)
    monkeypatch.setattr(lk,'_lo_cognition_route',lambda *a,**k: (_ for _ in ()).throw(AssertionError('cognition ran before referential JEV action')))
    calls=[]
    monkeypatch.setattr(lk,'_close_typed_referent',lambda obj: calls.append(obj.copy()) or 'close ok · terminal window closed')
    class WS:
        def begin_action(self,*a,**k): return {'mode':'deliberate','verify':True}
        def record_receipt(self,*a,**k): return {}
        def latest_receipts(self,*a,**k): return []
    monkeypatch.setattr(lk,'_world_state',lambda:WS())
    rc=lk.ollama_chat(initial_prompt='can you close that window',access_profile='power',workspace_override=tmp_path,one_shot=True)
    assert rc==0
    assert calls==[ref]
    out=capsys.readouterr().out
    assert 'Closed that window.' in out
    assert 'Unknown file tool' not in out


def test_current_action_referent_outranks_older_windows(monkeypatch):
    current={'id':'term_now','kind':'terminal_window','platform':'linux','pid_file':'/tmp/now.pid'}
    old={'id':'term_old','kind':'terminal_window','platform':'linux','pid_file':'/tmp/old.pid'}
    last={'tool':'run_command','args':{'command':'asciiquarium','new_terminal':True,'_referent':current},'path':'asciiquarium'}
    monkeypatch.setattr(lk,'_live_state_referents',lambda:[current,old])
    refs=lk._lo_recent_referents(last)
    assert refs[0]['id']=='term_now' and refs[0]['_salient'] is True
    decision=lk._jev_referential_intent('close that window',last)
    assert decision['object']['id']=='term_now'
