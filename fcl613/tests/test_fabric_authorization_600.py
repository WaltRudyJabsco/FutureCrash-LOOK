from core.endpoint_auth import EndpointAuth
from core.fabric_identity import FabricIdentity


def test_peer_token_is_required_and_redacted(tmp_path):
    a=FabricIdentity(tmp_path/'a'); b=FabricIdentity(tmp_path/'b')
    token='t'*48
    row=a.trust(b.ensure(),auth_token=token,endpoint='https://b.tail.example:7332')
    assert a.verify_peer(row['node_id'],token)
    assert not a.verify_peer(row['node_id'],'wrong')
    assert 'auth_token' not in a.trusted(public=True)['nodes'][row['node_id']]
    headers=a.auth_headers_for_url('https://b.tail.example:7332/v1/files/search')
    assert headers['X-Fabric-Node']==a.ensure()['node_id']
    assert headers['Authorization']=='Bearer '+token


def test_short_pair_code_is_numeric_and_attempt_limited(tmp_path):
    host=FabricIdentity(tmp_path/'host'); joiner=FabricIdentity(tmp_path/'joiner')
    invite=host.start_pairing('https://host.example:7332')
    assert len(invite['code'])==8 and invite['code'].isdigit()
    for _ in range(8):
        try: host.accept_pairing('00000000',joiner.ensure(),auth_token='z'*48)
        except ValueError: pass
    try: host.accept_pairing(invite['code'],joiner.ensure(),auth_token='z'*48)
    except ValueError as exc: assert 'locked' in str(exc) or 'no pairing' in str(exc)
    else: raise AssertionError('locked invitation was accepted')


def test_endpoint_pending_approval_and_trusted_cookie(tmp_path):
    auth=EndpointAuth(tmp_path/'endpoints.json')
    pending=auth.request(user_agent='Safari iPhone',remote='100.64.0.2')
    assert len(pending['code'])==6 and pending['code'].isdigit()
    assert auth.redeem_pending(pending['id']) is None
    auth.allow(pending['code'],'trust')
    issued=auth.redeem_pending(pending['id'],label='iPhone Safari')
    assert issued and issued['mode']=='trust'
    verified=auth.verify(issued['token'])
    assert verified['endpoint_id']==issued['endpoint_id']
    assert 'camera.offer' in verified['scopes']
    listing=auth.list()
    assert all('token_hash' not in row for row in listing['trusted'])
    assert auth.revoke(issued['endpoint_id'])
    assert auth.verify(issued['token']) is None


def test_endpoint_qr_invite_is_one_use(tmp_path):
    auth=EndpointAuth(tmp_path/'endpoints.json')
    invite=auth.create_invite('https://signal.example',mode='once')
    issued=auth.redeem_invite(invite['token'],label='Safari')
    assert issued and issued['mode']=='once'
    assert auth.redeem_invite(invite['token']) is None
