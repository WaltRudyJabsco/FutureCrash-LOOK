from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
LK=(ROOT/'look/lk').read_text()
NODE=(ROOT/'core/node.py').read_text()

def test_fabric_catalog_allows_remote_library_time():
    assert 'MEDIA_CATALOG_PEER_TIMEOUT = 8.0' in NODE
    assert 'ThreadPoolExecutor' in NODE
    assert '_peer_json(' in NODE
    assert '"/v1/media/catalog"' in NODE

def test_find_surfaces_partial_fabric_state():
    assert 'FABRIC PARTIAL' in LK
    assert 'unavailable: {failed}' in LK
    assert '_media_selector(rows,"FABRIC MEDIA FIND",query,catalog_meta)' in LK

def test_scan_without_root_discovers_standard_media():
    assert 'candidates=[home/"Music", home/"Movies"]' in LK
    assert 'Media.localized' in LK
    assert 'LOOK MEDIA DISCOVERY' in LK


def test_album_catalog_does_not_wait_for_sleeping_peer_discovery(monkeypatch):
    import threading
    from core import node
    entered=threading.Event();release=threading.Event();finished=threading.Event()
    def slow_refresh():
        entered.set()
        release.wait(3)
        finished.set()
    monkeypatch.setattr(node.PEERS,'refresh',slow_refresh)
    monkeypatch.setattr(node.PEERS,'public',lambda:[])
    monkeypatch.setattr(node,'node_info',lambda:{})
    monkeypatch.setattr(node,'_local_media_catalog',lambda:{'node':'local','count':1,'entries':[{'id':'new-album'}]})
    monkeypatch.setattr(node,'MEDIA_CATALOG_CACHE',{'data':None})
    try:
        result=node._fabric_media_catalog(force=True)
        assert entered.wait(1)
        assert not finished.is_set()
        assert result['entries']==[{'id':'new-album'}]
    finally:
        release.set()
        assert finished.wait(1)


def test_catalog_fallback_routes_share_a_total_budget(monkeypatch):
    from core import node
    clock=[0.0];calls=[]
    monkeypatch.setattr(node.time,'monotonic',lambda:clock[0])
    monkeypatch.setattr(node,'_peer_bases',lambda peer:['https://old','https://healthy','https://extra'])
    def request(url,timeout):
        calls.append((url,timeout));clock[0]+=timeout
        if 'healthy' in url:return {'entries':[{'id':'song'}]}
        raise TimeoutError('sleeping route')
    monkeypatch.setattr(node,'http_json',request)
    assert node._peer_json({},'/v1/media/catalog',timeout=8,total_timeout=12)['entries'][0]['id']=='song'
    assert calls==[('https://old/v1/media/catalog',8),('https://healthy/v1/media/catalog',4)]


def test_unpaired_tailscale_devices_are_not_missing_catalog_owners(monkeypatch):
    from core import node
    monkeypatch.setattr(node,'_refresh_media_peers_background',lambda:None)
    monkeypatch.setattr(node.PEERS,'public',lambda:[{'name':'phone','trusted':False,'node':{},'dns':'phone.example'}])
    monkeypatch.setattr(node,'node_info',lambda:{})
    monkeypatch.setattr(node,'_local_media_catalog',lambda:{'node':'m3','entries':[],'count':0})
    monkeypatch.setattr(node,'MEDIA_CATALOG_CACHE',{'data':None})
    result=node._fabric_media_catalog(force=True)
    assert result['errors']==[] and [row['node'] for row in result['nodes']]==['m3']
