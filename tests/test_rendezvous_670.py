import json
import time
from pathlib import Path

from core import node, rendezvous
from core.fabric_identity import FabricIdentity


def _fake_identity(tmp_path, name='a'):
    root=tmp_path/name
    root.mkdir(parents=True, exist_ok=True)
    # This is a real syntactically valid ssh-ed25519 public blob generated once for
    # tests; no private signing operation is needed in these unit tests.
    pub='ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIDUtlEq26Rz4hJkSxO8WshJSXN8S0oM6H0vB0XQb6m6b future-crash-look\n'
    (root/'node_ed25519.pub').write_text(pub)
    (root/'node_ed25519').write_text('TEST-PRIVATE-KEY\n')
    return FabricIdentity(root)


def test_pairwise_slot_is_stable_and_does_not_expose_token():
    token='x'*48
    slot=rendezvous.derive_slot(token)
    assert len(slot)==64
    assert slot==rendezvous.derive_slot(token)
    assert token not in slot
    assert slot!=rendezvous.derive_slot('y'*48)


def test_presence_uses_only_derived_slots(tmp_path, monkeypatch):
    identity=_fake_identity(tmp_path)
    peer=_fake_identity(tmp_path,'b').public(name='b')
    identity.trust(peer,auth_token='secret-token-'+'x'*32)
    monkeypatch.setattr(rendezvous,'_tailcat_advertisement',lambda:{'port':7443,'endpoints':['https://192.0.2.4:7443']})
    payload=rendezvous.build_presence(identity,now_value=1000,ttl=90)
    raw=json.dumps(payload)
    assert payload['schema']==rendezvous.PRESENCE_SCHEMA
    assert len(payload['slots'])==1
    assert 'secret-token-' not in raw
    assert payload['tailcat_port']==7443


def test_rendezvous_candidates_are_short_lived_and_keep_pinned_cert(tmp_path, monkeypatch):
    local=_fake_identity(tmp_path)
    remote=_fake_identity(tmp_path,'b').public(name='b')
    remote['transports']={'tailcat':{'endpoints':['https://b.local:7443'],'cert_pem':'CERT','cert_sha256':'abc'}}
    local.trust(remote,auth_token='t'*48)
    expires=time.time()+60
    assert local.learn_discovered_endpoints(remote['node_id'],['https://203.0.113.9:7443'],expires_at=expires)
    row=local.trusted()['nodes'][remote['node_id']]
    tc=row['transports']['tailcat']
    assert tc['cert_pem']=='CERT'
    assert tc['cert_sha256']=='abc'
    assert 'https://203.0.113.9:7443' in local._active_tailcat_endpoints(row,now_value=expires-1)
    assert 'https://203.0.113.9:7443' not in local._active_tailcat_endpoints(row,now_value=expires+1)


def test_peer_rows_include_live_rendezvous_candidate(tmp_path, monkeypatch):
    local=_fake_identity(tmp_path)
    remote=_fake_identity(tmp_path,'b').public(name='b')
    remote['transports']={'tailcat':{'endpoints':['https://b.local:7443'],'cert_pem':'CERT','cert_sha256':'abc'}}
    local.trust(remote,auth_token='t'*48)
    local.learn_discovered_endpoints(remote['node_id'],['https://203.0.113.9:7443'],expires_at=time.time()+60)
    monkeypatch.setattr(node,'FABRIC_IDENTITY',local)
    monkeypatch.setattr(node,'binary',lambda name: None if name=='tailscale' else None)
    rows=node.peer_rows()
    assert len(rows)==1
    assert 'https://203.0.113.9:7443' in rows[0]['tailcat_endpoints']


def test_registry_is_ephemeral_slot_scoped(monkeypatch):
    reg=rendezvous.Registry()
    payload={
        'schema':rendezvous.PRESENCE_SCHEMA,'version':'6.7.1','node_id':'fcl-test','public_key':'key',
        'name':'test','hostname':'test','issued_at':int(time.time()),'expires_at':int(time.time())+60,
        'tailcat_port':7443,'tailcat_endpoints':[],'slots':['a'*64],
    }
    monkeypatch.setattr(rendezvous,'verify_presence',lambda payload,signature: {})
    assert reg.put(payload,'sig','198.51.100.7')==1
    rows=reg.get('a'*64)
    assert len(rows)==1
    assert rows[0]['observed_endpoint']=='https://198.51.100.7:7443'
    assert reg.get('b'*64)==[]


def test_670_bundle_installs_rendezvous_and_keeps_tailscale_fallback():
    root=Path(__file__).resolve().parents[1]
    assert (root/'VERSION').read_text().strip()=='6.7.1'
    install=(root/'install.sh').read_text()
    lk=(root/'look/lk').read_text()
    node_text=(root/'core/node.py').read_text()
    assert 'core/rendezvous.py' in install
    assert 'core/fcl-rendezvous' in install
    assert 'import fabric_identity, endpoint_auth, intent_normalizer, tailcat, rendezvous' in install
    assert 'rendezvous' in node_text
    assert 'rendezvous [status|set URL|off|sync]' in lk
    assert 'tailscale serve --bg --https=7332' in install
