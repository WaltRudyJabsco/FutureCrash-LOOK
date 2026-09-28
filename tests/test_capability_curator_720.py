import importlib.machinery, importlib.util, sys, json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'core'))
import capability_curator, jev

loader=importlib.machinery.SourceFileLoader('look_lk_720',str(ROOT/'look'/'lk'))
spec=importlib.util.spec_from_loader(loader.name,loader)
lk=importlib.util.module_from_spec(spec); sys.modules[loader.name]=lk; loader.exec_module(lk)


def test_jev_window_actions_resolve_typed_referent():
    ref={'id':'term_a','kind':'terminal_window','command':'asciiquarium','platform':'linux'}
    cases={
        'maximize it':'maximize',
        'maximise that window':'maximize',
        'full screen it':'fullscreen',
        'fullscreen that window':'fullscreen',
        'focus it':'focus',
        'minimize ascii':'minimize',
    }
    for text,action in cases.items():
        d=jev.referential_action(text,[ref])
        assert d and d['action']==action and d['object']['id']=='term_a'


def test_curator_discovers_linux_without_mutating(monkeypatch,tmp_path):
    monkeypatch.setattr(capability_curator.platform,'system',lambda:'Linux')
    monkeypatch.setattr(capability_curator.platform,'node',lambda:'test-node')
    monkeypatch.setattr(capability_curator.shutil,'which',lambda n:'/usr/bin/'+n if n=='wmctrl' else None)
    path=tmp_path/'caps.json'
    data=capability_curator.refresh(path)
    ids={r['id'] for r in data['adapters']}
    assert {'linux-wmctrl','linux-process-handle'} <= ids
    assert capability_curator.supports('terminal_window','maximize',path)
    assert json.loads(path.read_text())['node']=='test-node'


def test_successful_action_promotes_adapter_to_proven(monkeypatch,tmp_path):
    monkeypatch.setattr(capability_curator.platform,'system',lambda:'Linux')
    monkeypatch.setattr(capability_curator.platform,'node',lambda:'n')
    monkeypatch.setattr(capability_curator.shutil,'which',lambda n:'/usr/bin/'+n if n=='wmctrl' else None)
    path=tmp_path/'caps.json'; capability_curator.refresh(path)
    capability_curator.record_result('linux-wmctrl','maximize',True,path)
    row=next(r for r in capability_curator.catalog(path,auto_refresh=False)['adapters'] if r['id']=='linux-wmctrl')
    assert row['state']=='proven' and row['successes']==1 and row['confidence']>=.99


def test_real_lo_maximize_turn_runs_before_cognition(tmp_path,monkeypatch,capsys):
    ref={'id':'term_1','kind':'terminal_window','platform':'linux','command':'asciiquarium','window_token':'LOOK-term_1'}
    prior={'tool':'run_command','path':'asciiquarium','args':{'command':'asciiquarium','new_terminal':True,'_referent':ref}}
    monkeypatch.setattr(lk,'_lo_latest_command_action',lambda:prior)
    monkeypatch.setattr(lk,'_lo_cognition_route',lambda *a,**k: (_ for _ in ()).throw(AssertionError('cognition ran')))
    calls=[]
    monkeypatch.setattr(lk,'_window_action_typed_referent',lambda obj,action: calls.append((obj.copy(),action)) or 'window maximize ok · terminal window maximized')
    class WS:
        def begin_action(self,*a,**k): return {'mode':'deliberate','verify':True}
        def record_receipt(self,*a,**k): return {}
        def latest_receipts(self,*a,**k): return []
    monkeypatch.setattr(lk,'_world_state',lambda:WS())
    assert lk.ollama_chat(initial_prompt='can you maximize it',access_profile='power',workspace_override=tmp_path,one_shot=True)==0
    assert calls==[(ref,'maximize')]
    assert 'Maximized that window.' in capsys.readouterr().out


def test_linux_launch_marks_window_with_stable_token(tmp_path,monkeypatch):
    lk.STATE_DIR=tmp_path/'state'; monkeypatch.setattr(lk.sys,'platform','linux')
    monkeypatch.setattr(lk.shutil,'which',lambda n:'/usr/bin/'+n if n in {'x-terminal-emulator','zsh'} else None)
    class P: pid=1234
    calls=[]; monkeypatch.setattr(lk.subprocess,'Popen',lambda argv,**kw:calls.append(argv) or P())
    args={}; result=lk._launch_command_new_terminal('asciiquarium',tmp_path,'/usr/bin/zsh',args)
    assert result.startswith('new terminal dispatch ok')
    token=args['_referent']['window_token']
    assert token.startswith('LOOK-term_') and token in calls[0][-1]


def test_installer_ships_and_refreshes_capability_curator():
    install=(ROOT/'install.sh').read_text()
    assert 'core/capability_curator.py' in install
    assert 'capability_curator.refresh()' in install
    assert 'installed capability curator differs from release' in install
