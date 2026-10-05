import importlib.machinery, importlib.util, sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'core'))
import live_state, jev

loader=importlib.machinery.SourceFileLoader('look_lk_730',str(ROOT/'look'/'lk'))
spec=importlib.util.spec_from_loader(loader.name,loader)
lk=importlib.util.module_from_spec(spec); sys.modules[loader.name]=lk; loader.exec_module(lk)


def _ref(i,command='asciiquarium'):
    return {'id':f'term_{i}','kind':'terminal_window','platform':'darwin','os_window_id':str(i),'command':command,'status':'open'}


def test_live_state_tracks_multiple_objects_and_current(tmp_path):
    path=tmp_path/'live.json'
    a=live_state.observe_object(_ref(1),path=path,current=True)
    b=live_state.observe_object(_ref(2),path=path,current=True)
    snap=live_state.snapshot(path=path)
    assert snap['current_object_id']=='term_2'
    assert {r['id'] for r in snap['objects']}=={'term_1','term_2'}
    assert live_state.current_object(path=path)['id']=='term_2'
    assert a['source']=='host_receipt' and b['confidence']==1.0


def test_close_retires_object_instead_of_leaving_historical_ghost(tmp_path):
    path=tmp_path/'live.json'; live_state.observe_object(_ref(1),path=path)
    live_state.retire_object(_ref(1),path=path,reason='closed_by_operator')
    assert live_state.active_objects(path=path)==[]
    raw=path.read_text()
    assert 'closed_by_operator' in raw


def test_jev_uses_salient_object_with_two_live_windows():
    a=_ref(1); b=_ref(2); b['_salient']=True
    d=jev.referential_action('close that window',[b,a])
    assert d and d['object']['id']=='term_2' and 'resolve:salient' in d['steps']
    other=jev.referential_action('close the other one',[b,a])
    assert other and other['object']['id']=='term_1' and 'resolve:other' in other['steps']


def test_named_window_stays_ambiguous_when_two_objects_match():
    refs=[_ref(1),_ref(2)]
    assert jev.referential_action('close asciiquarium window',refs) is None


def test_live_context_is_relevant_and_provenanced(tmp_path):
    path=tmp_path/'live.json'; live_state.observe_object(_ref(7),path=path)
    assert live_state.relevant_context('what is 2+2?',path=path)==''
    text=live_state.relevant_context('what windows are open?',path=path)
    assert 'LIVE STATE' in text and 'term_7' in text and 'host_receipt' in text


def test_lo_referents_use_live_state_not_durable_receipt_history(monkeypatch):
    current=_ref(2); old=_ref(1)
    last={'tool':'run_command','args':{'command':'asciiquarium','new_terminal':True,'_referent':current},'path':'asciiquarium'}
    monkeypatch.setattr(lk,'_live_state_referents',lambda:[current,old])
    refs=lk._lo_recent_referents(last)
    assert refs[0]['id']=='term_2' and refs[0]['_salient'] is True
    assert {r['id'] for r in refs}=={'term_1','term_2'}


def test_receipts_update_live_state(monkeypatch,tmp_path):
    lk.LIVE_STATE_FILE=tmp_path/'live.json'
    ref=_ref(9)
    class Typed: ok=True; status='dispatched'; message='new terminal dispatch ok'
    lk._live_state_after_receipt('run_command',{'command':'asciiquarium','_referent':ref},Typed())
    assert live_state.current_object(path=lk.LIVE_STATE_FILE)['id']=='term_9'
    class Closed: ok=True; status='effect_ok'; message='close ok'
    lk._live_state_after_receipt('object_action',{'object':ref,'intent':'close'},Closed())
    assert live_state.active_objects(path=lk.LIVE_STATE_FILE)==[]


def test_installer_ships_live_state_core():
    text=(ROOT/'install.sh').read_text()
    assert 'core/live_state.py' in text
    assert 'installed live-state core differs from release' in text
    assert 'import conductor, fabric_client, memory_store, decision, cognition, world_state, live_state' in text
