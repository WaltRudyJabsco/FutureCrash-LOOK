from core import fabric_client


class FakeIdentity:
    def auth_headers_for_url(self,url):
        return {"X-Fabric-Node":"fcl-test","Authorization":"Bearer secret"} if url.startswith("https://") else {}
    def ssl_context_for_url(self,url):
        return "PINNED" if url.startswith("https://") else None


def test_remote_json_adds_peer_authorization_and_tls_pin(monkeypatch):
    seen={}
    class Response:
        def __enter__(self): return self
        def __exit__(self,*a): pass
        def read(self): return b'{"ok":true}'
    def fake_urlopen(req,**kwargs):
        seen["headers"]={k.lower():v for k,v in req.header_items()}
        seen["kwargs"]=kwargs
        return Response()
    monkeypatch.setattr(fabric_client,"FABRIC_IDENTITY",FakeIdentity())
    monkeypatch.setattr(fabric_client.urllib.request,"urlopen",fake_urlopen)
    out=fabric_client._json("https://peer.local:7443/v1/jobs",{"x":1},timeout=3)
    assert out["ok"] is True
    assert seen["headers"]["x-fabric-node"]=="fcl-test"
    assert seen["headers"]["authorization"]=="Bearer secret"
    assert seen["kwargs"]["context"]=="PINNED"


def test_endpoint_base_prefers_active_native_transport():
    snap={"self":{"name":"m4"},"peers":[{"name":"3090","dns":"3090.tail.test","url":"https://3090.local:7443","tailcat_endpoints":["https://192.0.2.3:7443"],"node":{"identity":{"name":"3090"}}}]}
    assert fabric_client._endpoint_base(snap,"3090","3090.tail.test","http://127.0.0.1:7332")=="https://3090.local:7443"
    assert fabric_client._endpoint_base(snap,"m4",None,"http://127.0.0.1:7332")=="http://127.0.0.1:7332"


def test_stream_code_uses_authenticated_open():
    source=open(fabric_client.__file__,encoding="utf-8").read()
    assert 'headers.update(FABRIC_IDENTITY.auth_headers_for_url(endpoint))' in source
    assert 'with _open(req,url=endpoint,timeout=timeout) as response:' in source
