import pytest
from core import node


@pytest.mark.parametrize('trusted',[True,False])
def test_restart_retry_distinguishes_trusted_from_unknown_devices(monkeypatch,trusted):
    peer={'name':'peer','dns':'peer.example','online':True,'trusted':trusted,'tailcat_endpoints':['https://peer:7443']}
    monkeypatch.setattr(node,'peer_rows',lambda:[peer])
    monkeypatch.setattr(node,'now',lambda:100.0)
    monkeypatch.setattr(node.random,'uniform',lambda *a:0.0)
    monkeypatch.setattr(node,'http_json',lambda *a,**kw:(_ for _ in ()).throw(OSError('service restarting')))
    registry=node.PeerRegistry();registry.refresh()
    expected=node.PEER_NODE_REFRESH_SECONDS if trusted else node.PEER_UNKNOWN_BACKOFF_SECONDS
    assert registry.state['peer.example']['next_due']==100+expected
    assert registry.public()[0].get('node') is None
