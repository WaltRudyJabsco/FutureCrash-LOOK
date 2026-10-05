from pathlib import Path

from core.fabric_identity import FabricIdentity
from core.endpoint_auth import EndpointAuth
from core import node, tailcat


def test_tailcat_certificate_is_pinned_in_trust(tmp_path, monkeypatch):
    root=tmp_path/'tailcat'
    monkeypatch.setattr(tailcat,'STATE_ROOT',root)
    monkeypatch.setattr(tailcat,'KEY_PATH',root/'tls-key.pem')
    monkeypatch.setattr(tailcat,'CERT_PATH',root/'tls-cert.pem')
    monkeypatch.setattr(tailcat,'AD_PATH',root/'advertisement.json')
    ad=tailcat.ensure_identity(7443)
    assert ad['schema']=='tailcat-transport-v1'
    assert ad['cert_pem'].startswith('-----BEGIN CERTIFICATE-----')
    assert ad['endpoints']

    a=FabricIdentity(tmp_path/'a'); b=FabricIdentity(tmp_path/'b')
    peer=b.ensure(); peer['transports']={'tailcat':ad}
    token='x'*48
    a.trust(peer,auth_token=token,endpoint='https://peer.tail.example:7332')
    url=ad['endpoints'][0]+'/v1/advertisement'
    assert a.ssl_context_for_url(url) is not None
    headers=a.auth_headers_for_url(url)
    assert headers['Authorization']=='Bearer '+token


def test_peer_rows_survive_without_tailscale_when_tailcat_is_trusted(tmp_path, monkeypatch):
    local=FabricIdentity(tmp_path/'local'); peer=FabricIdentity(tmp_path/'peer')
    remote=peer.ensure(); remote['name']='peerbox'; remote['hostname']='peerbox'
    remote['transports']={'tailcat':{'endpoints':['https://192.0.2.44:7443'],'cert_pem':'CERT','cert_sha256':'abc'}}
    local.trust(remote,auth_token='y'*48)
    monkeypatch.setattr(node,'FABRIC_IDENTITY',local)
    monkeypatch.setattr(node,'binary',lambda name: None)
    rows=node.peer_rows()
    assert len(rows)==1
    assert rows[0]['name']=='peerbox'
    assert rows[0]['tailcat_endpoints']==['https://192.0.2.44:7443']


def test_endpoint_approval_routes_to_owning_fabric_node(tmp_path, monkeypatch):
    local_auth=EndpointAuth(tmp_path/'local-endpoints.json')
    monkeypatch.setattr(node,'ENDPOINT_AUTH',local_auth)
    monkeypatch.setattr(node,'identity',lambda:{'name':'m4'})
    monkeypatch.setattr(node,'node_info',lambda:{'name':'m4'})
    peer={'name':'3090','url':'https://192.0.2.30:7443','node':{'identity':{'name':'3090'}}}
    monkeypatch.setattr(node.PEERS,'public',lambda:[peer])

    calls=[]
    def fake_http(url, data=None, timeout=0):
        calls.append((url,data))
        if url.endswith('/v1/endpoints'):
            return {'pending':[{'code':'482193','user_agent':'iPad Safari'}], 'trusted':[], 'sessions':[]}
        if url.endswith('/v1/endpoints/allow'):
            assert data=={'code':'482193','mode':'trust'}
            return {'ok':True,'endpoint':{'code':'482193','approved':'trust'}}
        raise AssertionError(url)
    monkeypatch.setattr(node,'http_json',fake_http)
    result=node._endpoint_allow_fabric('482193','trust')
    assert result['node']=='3090'
    assert result['endpoint']['approved']=='trust'
    assert any(url.endswith('/v1/endpoints/allow') for url,_ in calls)

def test_transport_refresh_preserves_existing_authorization(tmp_path):
    local=FabricIdentity(tmp_path/'local'); peer=FabricIdentity(tmp_path/'peer')
    token='z'*48
    original=peer.ensure()
    local.trust(original,auth_token=token,endpoint='https://peer.tail.example:7332')
    refreshed=dict(original)
    refreshed['transports']={'tailcat':{'endpoints':['https://peer.local:7443'],'cert_pem':'CERT','cert_sha256':'abc'}}
    local.trust(refreshed,source='transport-refresh')
    stored=local.trusted()['nodes'][original['node_id']]
    assert stored['auth_token']==token
    assert stored['transports']['tailcat']['endpoints']==['https://peer.local:7443']
