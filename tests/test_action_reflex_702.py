from pathlib import Path
import importlib.machinery, importlib.util, sys, time

ROOT=Path(__file__).resolve().parents[1]
loader=importlib.machinery.SourceFileLoader('look_lk_702',str(ROOT/'look'/'lk'))
spec=importlib.util.spec_from_loader(loader.name,loader)
lk=importlib.util.module_from_spec(spec); sys.modules[loader.name]=lk; loader.exec_module(lk)


def test_explicit_terminal_command_is_host_reflex():
    action=lk._lo_explicit_command_action('run asciiquarium in the terminal')
    assert action == {'tool':'run_command','args':{'command':'asciiquarium','interactive':True},'path':'asciiquarium'}
    assert lk._lo_explicit_command_action('launch asciiquarium in the terminal')['args']['interactive'] is True


def test_single_token_run_is_unambiguous_even_when_not_installed(monkeypatch):
    monkeypatch.setattr(lk.shutil,'which',lambda name: None)
    action=lk._lo_explicit_command_action('run asciiquarium')
    assert action['args']['command']=='asciiquarium'


def test_ambiguous_natural_language_run_still_uses_cognition(monkeypatch):
    monkeypatch.setattr(lk.shutil,'which',lambda name: None)
    assert lk._lo_explicit_command_action('run the tests') is None


def test_recent_typed_command_receipt_restores_retry_referent(monkeypatch):
    class WS:
        def latest_receipts(self,limit):
            return [{'action':'run_command','observed_at':time.time(),'args':{'command':'asciiquarium','interactive':True}}]
    monkeypatch.setattr(lk,'_world_state',lambda:WS())
    action=lk._lo_latest_command_action()
    assert action['path']=='asciiquarium'
    assert lk._lo_action_continuation('try again',action)


def test_stale_command_receipt_does_not_become_cross_session_again(monkeypatch):
    class WS:
        def latest_receipts(self,limit):
            return [{'action':'run_command','observed_at':time.time()-lk._LO_RETRY_ACTION_MAX_AGE_SECONDS-1,'args':{'command':'asciiquarium'}}]
    monkeypatch.setattr(lk,'_world_state',lambda:WS())
    assert lk._lo_latest_command_action() is None


def test_real_lo_turn_executes_explicit_command_before_cognition(tmp_path,monkeypatch,capsys):
    calls=[]
    stale={'tool':'run_command','args':{'command':'asciiquarium','interactive':True},'path':'asciiquarium'}
    monkeypatch.setattr(lk,'_lo_latest_command_action',lambda:stale)
    monkeypatch.setattr(lk,'_lo_cognition_route',lambda *a,**k: (_ for _ in ()).throw(AssertionError('cognition ran before explicit command')))
    monkeypatch.setattr(lk,'_run_command_tool',lambda workspace,args,profile: calls.append((args.copy(),profile)) or 'interactive exit 130 · launched; terminal session interrupted by user')
    # Keep this routing test isolated from the user's real persistent state.
    class WS:
        def begin_action(self,*a,**k): return {'mode':'deliberate','verify':True}
        def record_receipt(self,*a,**k): return {}
        def latest_receipts(self,*a,**k): return []
    monkeypatch.setattr(lk,'_world_state',lambda:WS())
    rc=lk.ollama_chat(initial_prompt='run asciiquarium in the terminal',access_profile='power',workspace_override=tmp_path,one_shot=True)
    assert rc==0
    assert calls==[({'command':'asciiquarium','interactive':True},'power')]
    out=capsys.readouterr().out
    assert 'asciiquarium' in out
    assert 'interrupted' in out.casefold()

def test_bare_repeat_of_exact_last_command_is_deterministic():
    action={'tool':'run_command','args':{'command':'asciiquarium','interactive':True},'path':'asciiquarium'}
    assert lk._lo_action_continuation('asciiquarium',action)


def test_retry_rechecks_current_authority(tmp_path,monkeypatch,capsys):
    action={'tool':'run_command','args':{'command':'asciiquarium','interactive':True},'path':'asciiquarium'}
    monkeypatch.setattr(lk,'_lo_latest_command_action',lambda:action)
    monkeypatch.setattr(lk,'_run_command_tool',lambda *a,**k: (_ for _ in ()).throw(AssertionError('workspace retry reached shell')))
    monkeypatch.setattr(lk,'_lo_cognition_route',lambda *a,**k: (_ for _ in ()).throw(AssertionError('retry reached cognition')))
    rc=lk.ollama_chat(initial_prompt='try again',access_profile='workspace',workspace_override=tmp_path,one_shot=True)
    assert rc==0
    assert 'unavailable in this access profile' in capsys.readouterr().out
