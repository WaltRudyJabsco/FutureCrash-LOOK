import importlib.machinery, importlib.util, sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'core'))
import jev, live_state, observation

loader=importlib.machinery.SourceFileLoader('look_lk_740',str(ROOT/'look'/'lk'))
spec=importlib.util.spec_from_loader(loader.name,loader)
lk=importlib.util.module_from_spec(spec); sys.modules[loader.name]=lk; loader.exec_module(lk)


def _ref(i,created,command='asciiquarium'):
    return {'id':f'term_{i}','kind':'terminal_window','platform':'linux','command':command,'status':'open','created_at':created}


def test_another_reuses_salient_prior_command_not_literal_another():
    d=jev.command_imperative('run another in a new terminal',prior={'command':'asciiquarium','new_terminal':True})
    assert d and d['command']=='asciiquarium' and d['terminal']=='new'
    assert 'resolve:another-prior-command' in d['steps']


def test_first_named_window_is_relational_selection_not_guess():
    refs=[_ref(1,10),_ref(2,20),_ref(3,30,'htop')]
    d=jev.referential_action('close the first ascii window',refs)
    assert d and d['object']['id']=='term_1'
    assert 'resolve:ordinal:first' in d['steps']


def test_plain_named_window_remains_ambiguous_with_two_matches():
    refs=[_ref(1,10),_ref(2,20)]
    assert jev.referential_action('close ascii window',refs) is None


def test_windows_query_is_first_class_jev_observation():
    d=jev.state_query('what windows are open')
    assert d=={'kind':'state_query','domain':'windows','relation':'open','confidence':1.0,'steps':['query:windows','relation:open']}


def test_live_state_reconciles_observed_pid_to_existing_stable_object(tmp_path):
    path=tmp_path/'live.json'
    live_state.observe_object({'id':'term_a','kind':'terminal_window','platform':'linux','pid':4321,'command':'asciiquarium'},path=path)
    live_state.reconcile_domain('windows',[{'id':'win_abc','kind':'desktop_window','platform':'linux','pid':4321,'title':'LOOK terminal'}],path=path,source='linux-wmctrl_inspector',authoritative=True)
    rows=live_state.active_objects(path=path,refresh_now=False)
    assert len(rows)==1 and rows[0]['id']=='term_a'
    assert rows[0]['title']=='LOOK terminal'


def test_state_query_real_turn_skips_cognition(tmp_path,monkeypatch,capsys):
    snap={'current_object_id':'term_2','objects':[
        {'id':'term_1','kind':'terminal_window','command':'asciiquarium','status':'open'},
        {'id':'term_2','kind':'terminal_window','command':'asciiquarium','status':'open'},
    ],'facts':[{'key':'observation.windows','value':{'authoritative':True}}]}
    monkeypatch.setattr(lk,'_observe_live_state',lambda domain='windows':snap)
    monkeypatch.setattr(lk,'_lo_cognition_route',lambda *a,**k: (_ for _ in ()).throw(AssertionError('cognition should not answer state query')))
    rc=lk.ollama_chat(initial_prompt='what windows are open',access_profile='power',workspace_override=tmp_path,one_shot=True)
    assert rc==0
    out=capsys.readouterr().out
    assert 'Observed open windows:' in out and out.count('asciiquarium')>=2


def test_observation_linux_parser_maps_look_token(monkeypatch):
    monkeypatch.setattr(observation.sys,'platform','linux')
    monkeypatch.setenv('DISPLAY',':0')
    monkeypatch.setattr(observation.shutil,'which',lambda n:'/usr/bin/wmctrl' if n=='wmctrl' else None)
    sample='0x04a00007  0  4321  10 20 800 600  XTerm.XTerm host LOOK-term_abc123\n'
    monkeypatch.setattr(observation,'_run',lambda *a,**k: sample)
    row=observation.observe_windows()['objects'][0]
    assert row['id']=='term_abc123' and row['kind']=='terminal_window' and row['pid']==4321


def test_installer_ships_observation_plane():
    text=(ROOT/'install.sh').read_text()
    assert 'core/observation.py' in text
    assert 'installed observation plane differs from release' in text
    assert 'import observation' in text

def test_observed_focus_becomes_current_object(tmp_path):
    path=tmp_path/'live.json'
    live_state.observe_object(_ref(1,10),path=path,current=True)
    live_state.observe_object(_ref(2,20),path=path,current=False)
    live_state.reconcile_domain('windows',[
        {'id':'term_1','kind':'terminal_window','focused':False},
        {'id':'term_2','kind':'terminal_window','focused':True},
    ],path=path,source='window_inspector',authoritative=True)
    assert live_state.current_object(path=path)['id']=='term_2'


def test_stale_unrefreshable_objects_fall_out_of_snapshot(tmp_path,monkeypatch):
    path=tmp_path/'live.json'
    monkeypatch.setattr(live_state,'_now',lambda:100.0)
    live_state.observe_object({'id':'term_old','kind':'terminal_window','platform':'darwin','command':'asciiquarium'},path=path,ttl=5)
    monkeypatch.setattr(live_state,'_now',lambda:106.0)
    assert live_state.snapshot(path=path)['objects']==[]
