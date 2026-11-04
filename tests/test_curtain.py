import importlib.util
from pathlib import Path
import pytest
spec=importlib.util.spec_from_file_location('curtain',Path(__file__).resolve().parents[1]/'core/curtain.py')
curtain=importlib.util.module_from_spec(spec);spec.loader.exec_module(curtain)

@pytest.fixture(autouse=True)
def isolated(tmp_path,monkeypatch):
    monkeypatch.setattr(curtain,'path',lambda:tmp_path/'state.json')
    monkeypatch.setattr(curtain,'desktop',lambda:'launch requested')

def request(action,**fields):return curtain.operate(dict(action=action,**fields),'test-node',[],lambda *_:None)

def test_setup_lock_unlock_and_private_storage():
    assert not request('status')['configured']
    request('setup',pin='1234')
    assert curtain.path().stat().st_mode&0o777==0o600
    assert '1234' not in curtain.path().read_text()
    assert 'verifier' not in request('status')
    assert request('lock')['locked']
    with pytest.raises(ValueError,match='Incorrect'):request('unlock',pin='9999')
    assert request('unlock',pin='1234')['locked'] is False

def test_pin_rotation_requires_current_pin_and_unlocked():
    request('setup',pin='1234')
    with pytest.raises(ValueError):request('setup',pin='5678')
    request('lock')
    with pytest.raises(ValueError):request('setup',pin='5678',old_pin='1234')
    request('unlock',pin='1234');request('setup',pin='5678',old_pin='1234')
    request('lock');assert not request('unlock',pin='5678')['locked']

def test_throttling_survives_relock(monkeypatch):
    request('setup',pin='1234');request('lock')
    for _ in range(5):
        with pytest.raises(ValueError):request('unlock',pin='9999')
    request('lock')
    with pytest.raises(ValueError,match='Too many'):request('unlock',pin='1234')
    future=curtain.time.time()+31;monkeypatch.setattr(curtain.time,'time',lambda:future)
    assert not request('unlock',pin='1234')['locked']

def test_delivery_partial_and_stale_event():
    events=[]
    def send(peer,payload):
        events.append(payload['event'])
        if peer=='offline':raise OSError('secret connection details')
        return {'ok':True}
    result=curtain.operate({'action':'setup','pin':'1234'},'test-node',['online','offline'],send)
    assert not result['ok'] and len(result['delivery'])==3
    assert 'secret' not in str(result)
    request('lock');assert curtain.apply(events[0])['stale']
    assert request('status')['locked']

def test_verifier_and_caption_validation():
    with pytest.raises(ValueError):request('setup',pin='abcd')
    request('setup',pin='1234')
    event=curtain.load();event['revision']+=1;event['captions']=['\x1b[31m']
    with pytest.raises(ValueError):curtain.apply(event)
    event['captions']=['QUIET WATCH'];event['locked']=True
    assert curtain.apply(event)['captions']==['QUIET WATCH']

def test_setup_required_and_replay_idempotent():
    with pytest.raises(ValueError,match='Set a PIN'):request('lock')
    request('setup',pin='1234');event=curtain.load()
    assert curtain.apply(event)['stale']

def test_three_node_unlock_converges_without_plaintext_pin(tmp_path,monkeypatch):
    peers={}
    for name in ('a','b','c'):
        instance=importlib.util.module_from_spec(spec);spec.loader.exec_module(instance)
        monkeypatch.setattr(instance,'path',lambda name=name:tmp_path/(name+'.json'))
        monkeypatch.setattr(instance,'desktop',lambda:'launch requested')
        peers[name]=instance
    messages=[]
    def run(name,action,**fields):
        def send(target,payload):
            messages.append(payload)
            return peers[target].apply(payload['event'])
        return peers[name].operate(dict(action=action,**fields),name,[key for key in peers if key!=name],send)
    run('a','setup',pin='1234');run('b','lock',captions=['QUIET WATCH'])
    assert all(peer.public()['locked'] for peer in peers.values())
    assert all(peer.public()['captions']==['QUIET WATCH'] for peer in peers.values())
    run('c','unlock',pin='1234')
    assert not any(peer.public()['locked'] for peer in peers.values())
    assert all('pin' not in payload and 'pin' not in payload['event'] for payload in messages)

def test_portable_setup_without_scrypt(monkeypatch):
    monkeypatch.delattr(curtain.hashlib,'scrypt',raising=False)
    request('setup',pin='1234');request('lock')
    assert curtain.load()['kdf']=='pbkdf2-sha256'
    assert not request('unlock',pin='1234')['locked']

def test_legacy_scrypt_record_and_rotation():
    if not hasattr(curtain.hashlib,'scrypt'):pytest.skip('Legacy scrypt unavailable')
    request('setup',pin='1234');state=curtain.load()
    state.pop('kdf');state['verifier']=curtain.pin_hash('1234',state['salt'],'scrypt');curtain.save(state)
    request('setup',pin='5678',old_pin='1234')
    assert curtain.load()['kdf']=='pbkdf2-sha256'
    assert not request('unlock',pin='5678')['locked']
