import json
from pathlib import Path

from core.fabric_identity import FabricIdentity, normalize_pair_code, parse_pair_target, public_identity


def test_identity_is_stable_and_public_key_derived(tmp_path):
    store=FabricIdentity(tmp_path/'identity')
    first=store.ensure(); second=store.ensure()
    assert first['node_id']==second['node_id']
    assert first['fingerprint']==second['fingerprint']
    assert first['node_id'].startswith('fcl-')
    assert first['algorithm']=='ssh-ed25519'
    assert (tmp_path/'identity/node_ed25519').stat().st_mode & 0o777 == 0o600


def test_trust_recomputes_identity_from_key(tmp_path):
    a=FabricIdentity(tmp_path/'a'); b=FabricIdentity(tmp_path/'b')
    peer=b.ensure()
    stored=a.trust(peer)
    assert stored['node_id']==peer['node_id']
    bad=dict(peer); bad['node_id']='fcl-deadbeef'
    try:
        a.trust(bad)
    except ValueError as exc:
        assert 'does not match' in str(exc)
    else:
        raise AssertionError('mismatched node id was trusted')


def test_pairing_invitation_is_one_use(tmp_path):
    host=FabricIdentity(tmp_path/'host'); joiner=FabricIdentity(tmp_path/'joiner')
    invite=host.start_pairing('https://fabric.example:7332', name='host')
    endpoint, code=parse_pair_target(invite['uri'])
    assert endpoint=='https://fabric.example:7332'
    assert normalize_pair_code(code)==normalize_pair_code(invite['code'])
    accepted=host.accept_pairing(code, joiner.ensure())
    assert accepted['node_id']==joiner.ensure()['node_id']
    assert joiner.ensure()['node_id'] in host.trusted()['nodes']
    try:
        host.accept_pairing(code, joiner.ensure())
    except ValueError as exc:
        assert 'no pairing invitation' in str(exc)
    else:
        raise AssertionError('pairing invitation was reusable')
