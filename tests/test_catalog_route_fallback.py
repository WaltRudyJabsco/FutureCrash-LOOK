from core import node


def test_bulk_catalog_tries_dns_before_second_lan_and_remembers_success(monkeypatch):
    peer={'url':'https://laptop.local:7443','dns':'laptop.example.net',
          'tailcat_endpoints':['https://192.168.1.2:7443','https://laptop.example.net:7443']}
    monkeypatch.setattr(node,'MEDIA_CATALOG_ROUTES',{})
    clock=[0.0];monkeypatch.setattr(node.time,'monotonic',lambda:clock[0])
    calls=[]
    def fetch(url,timeout):
        calls.append((url,timeout))
        if '.local' in url:clock[0]+=timeout;raise TimeoutError('bulk read stalled')
        return {'entries':[]}
    monkeypatch.setattr(node,'http_json',fetch)
    assert node._peer_json(peer,'/v1/media/catalog',timeout=8,total_timeout=18)=={'entries':[]}
    assert [url for url,_ in calls]==['https://laptop.local:7443/v1/media/catalog','https://laptop.example.net:7443/v1/media/catalog']
    calls.clear();node._peer_json(peer,'/v1/media/catalog',timeout=8,total_timeout=18)
    assert len(calls)==1 and 'laptop.example.net' in calls[0][0]
    clock[0]+=node.MEDIA_CATALOG_ROUTE_TTL_SECONDS+1
    calls.clear();node._peer_json(peer,'/v1/media/catalog',timeout=8,total_timeout=18)
    assert '.local' in calls[0][0]


def test_control_routes_keep_order_and_catalog_obeys_budget(monkeypatch):
    peer={'url':'https://laptop.local:7443','dns':'laptop.example.net',
          'tailcat_endpoints':['https://192.168.1.2:7443','https://laptop.example.net:7443']}
    calls=[];clock=[0.0]
    monkeypatch.setattr(node,'MEDIA_CATALOG_ROUTES',{})
    monkeypatch.setattr(node.time,'monotonic',lambda:clock[0])
    def fetch(url,timeout):
        calls.append((url,timeout));clock[0]+=timeout;raise TimeoutError('offline')
    monkeypatch.setattr(node,'http_json',fetch)
    import pytest
    with pytest.raises(RuntimeError):node._peer_json(peer,'/v1/node',timeout=2,total_timeout=3)
    assert calls[1]==('https://192.168.1.2:7443/v1/node',1)
    calls.clear();clock[0]=0
    with pytest.raises(RuntimeError):node._peer_json(peer,'/v1/media/catalog',timeout=8,total_timeout=10)
    assert calls[1]==('https://laptop.example.net:7443/v1/media/catalog',2)
    assert clock[0]==10
