from pathlib import Path
import importlib.machinery, importlib.util, sys

ROOT=Path(__file__).resolve().parents[1]
loader=importlib.machinery.SourceFileLoader('look_lk_703',str(ROOT/'look'/'lk'))
spec=importlib.util.spec_from_loader(loader.name,loader)
lk=importlib.util.module_from_spec(spec); sys.modules[loader.name]=lk; loader.exec_module(lk)


def test_single_token_run_is_direct_even_when_unknown(monkeypatch):
    monkeypatch.setattr(lk.shutil,'which',lambda name: None)
    intent=lk._jev_command_intent('run asciiquarium')
    assert intent['args']=={'command':'asciiquarium','interactive':False}
    assert intent['jev']['tokens']==1


def test_again_is_semantic_modifier_not_argv(monkeypatch):
    monkeypatch.setattr(lk.shutil,'which',lambda name: None)
    intent=lk._jev_command_intent('run asciiquarium again')
    assert intent['args']['command']=='asciiquarium'
    assert intent['jev']['retry'] is True
    assert 'again' not in intent['args']['command']


def test_new_terminal_is_semantic_modifier_not_argv(monkeypatch):
    monkeypatch.setattr(lk.shutil,'which',lambda name: None)
    intent=lk._jev_command_intent('run asciiquarium in a new terminal')
    assert intent['args']=={'command':'asciiquarium','interactive':False,'new_terminal':True}
    assert intent['jev']['terminal']=='new'


def test_combined_modifiers_peel_in_either_order(monkeypatch):
    monkeypatch.setattr(lk.shutil,'which',lambda name: None)
    a=lk._jev_command_intent('run asciiquarium again in a new terminal')
    b=lk._jev_command_intent('run asciiquarium in a new terminal again')
    for intent in (a,b):
        assert intent['args']['command']=='asciiquarium'
        assert intent['args']['new_terminal'] is True
        assert intent['jev']['retry'] is True


def test_multiword_real_executable_keeps_real_arguments(monkeypatch):
    monkeypatch.setattr(lk.shutil,'which',lambda name: '/usr/bin/python' if name=='python' else None)
    intent=lk._jev_command_intent('run python script.py --fast')
    assert intent['args']['command']=='python script.py --fast'
    assert intent['jev']['tokens']==3


def test_multiword_natural_language_falls_back_to_cognition(monkeypatch):
    monkeypatch.setattr(lk.shutil,'which',lambda name: None)
    assert lk._jev_command_intent('run the tests') is None
    assert lk._jev_command_intent('run my backup job') is None


def test_again_inherits_prior_terminal_mode_only_for_same_command(monkeypatch):
    monkeypatch.setattr(lk.shutil,'which',lambda name: None)
    last={'tool':'run_command','path':'asciiquarium','args':{'command':'asciiquarium','new_terminal':True,'interactive':False}}
    same=lk._jev_command_intent('run asciiquarium again',last)
    other=lk._jev_command_intent('run cowsay again',last)
    assert same['args']['new_terminal'] is True
    assert 'new_terminal' not in other['args']


def test_new_terminal_dispatch_is_typed_success(tmp_path,monkeypatch):
    monkeypatch.setattr(lk.sys,'platform','linux')
    monkeypatch.setattr(lk.shutil,'which',lambda name: '/bin/zsh' if name=='zsh' else ('/usr/bin/x-terminal-emulator' if name=='x-terminal-emulator' else None))
    calls=[]
    class P: pass
    monkeypatch.setattr(lk.subprocess,'Popen',lambda argv,**kw: calls.append((argv,kw)) or P())
    result=lk._run_command_tool(tmp_path,{'command':'asciiquarium','new_terminal':True},'unsafe')
    assert result.startswith('new terminal dispatch ok')
    assert calls
    assert calls[0][0][-1]=='asciiquarium'
    typed=lk._command_result(result)
    assert typed.ok is True and typed.status=='dispatched'


def test_new_terminal_failure_is_not_success(tmp_path,monkeypatch):
    monkeypatch.setattr(lk.sys,'platform','linux')
    monkeypatch.setattr(lk.shutil,'which',lambda name: '/bin/zsh' if name=='zsh' else None)
    result=lk._run_command_tool(tmp_path,{'command':'asciiquarium','new_terminal':True},'unsafe')
    assert result.startswith('New terminal dispatch failed:')
    assert lk._command_result(result).ok is False


def test_real_lo_turn_strips_new_terminal_modifier_before_execution(tmp_path,monkeypatch,capsys):
    calls=[]
    monkeypatch.setattr(lk,'_lo_cognition_route',lambda *a,**k: (_ for _ in ()).throw(AssertionError('cognition ran before JEV command')))
    monkeypatch.setattr(lk,'_run_command_tool',lambda workspace,args,profile: calls.append(args.copy()) or 'new terminal dispatch ok · command launched')
    class WS:
        def begin_action(self,*a,**k): return {'mode':'deliberate','verify':True}
        def record_receipt(self,*a,**k): return {}
        def latest_receipts(self,*a,**k): return []
    monkeypatch.setattr(lk,'_world_state',lambda:WS())
    rc=lk.ollama_chat(initial_prompt='run asciiquarium in a new terminal',access_profile='power',workspace_override=tmp_path,one_shot=True)
    assert rc==0
    assert calls==[{'command':'asciiquarium','interactive':False,'new_terminal':True}]
    out=capsys.readouterr().out
    assert 'COMMAND  asciiquarium' in out
    assert 'in a new terminal' in out


def test_real_lo_turn_strips_again_before_execution(tmp_path,monkeypatch,capsys):
    calls=[]
    prior={'tool':'run_command','path':'asciiquarium','args':{'command':'asciiquarium','interactive':True}}
    monkeypatch.setattr(lk,'_lo_latest_command_action',lambda:prior)
    monkeypatch.setattr(lk,'_lo_cognition_route',lambda *a,**k: (_ for _ in ()).throw(AssertionError('cognition ran before JEV command')))
    monkeypatch.setattr(lk,'_run_command_tool',lambda workspace,args,profile: calls.append(args.copy()) or 'interactive exit 0 · terminal session completed')
    class WS:
        def begin_action(self,*a,**k): return {'mode':'deliberate','verify':True}
        def record_receipt(self,*a,**k): return {}
        def latest_receipts(self,*a,**k): return []
    monkeypatch.setattr(lk,'_world_state',lambda:WS())
    rc=lk.ollama_chat(initial_prompt='run asciiquarium again',access_profile='power',workspace_override=tmp_path,one_shot=True)
    assert rc==0
    assert calls==[{'command':'asciiquarium','interactive':True}]
    assert 'COMMAND  asciiquarium' in capsys.readouterr().out
