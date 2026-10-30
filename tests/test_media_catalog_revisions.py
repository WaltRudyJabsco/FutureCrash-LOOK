import threading
import time
from core import node
from test_media_request_regressions import lk


def test_catalog_revision_tracks_metadata_and_visibility_without_build(tmp_path,monkeypatch):
    library=tmp_path/'media_library.json';library.write_text('{}')
    monkeypatch.setattr(node,'LOOK_MEDIA_LIBRARY',library)
    monkeypatch.setattr(node,'identity',lambda:{'name':'owner'})
    monkeypatch.setattr(node,'_build_local_media_catalog',lambda:(_ for _ in ()).throw(AssertionError('full catalog build')))
    first=node._local_media_catalog_revision()
    assert node._local_media_catalog_revision()==first
    library.write_text('{"title":"renamed"}')
    second=node._local_media_catalog_revision();assert first!=second
    (tmp_path/'media_owner_visibility.json').write_text('{"paths":["/hidden"]}')
    assert node._local_media_catalog_revision()!=second


def test_expired_snapshot_returns_without_waiting_for_slow_peer(tmp_path,monkeypatch):
    library=tmp_path/'library';library.write_text('{}')
    monkeypatch.setattr(node,'LOOK_MEDIA_LIBRARY',library)
    old={'entries':[{'id':'Berlin'}]}
    cache={'at':1,'data':old,'local_mtime_ns':library.stat().st_mtime_ns}
    monkeypatch.setattr(node,'MEDIA_CATALOG_CACHE',cache)
    monkeypatch.setattr(node,'MEDIA_CATALOG_BUILD_LOCK',threading.Lock())
    entered=threading.Event();release=threading.Event();done=threading.Event();calls=[]
    def slow(force=False):
        calls.append(1);entered.set();release.wait(3)
        cache.update(data={'entries':[{'id':'Berlin'},{'id':'new'}]},at=node.now())
        done.set()
    monkeypatch.setattr(node,'_build_fabric_media_catalog',slow)
    try:
        result=node._fabric_media_catalog()
        assert entered.wait(1) and not done.is_set()
        assert result['entries']==old['entries'] and result['refreshing']
        assert node._fabric_media_catalog()['entries']==old['entries']
        assert calls==[1]
    finally:
        release.set();assert done.wait(1)
        with node.MEDIA_CATALOG_BUILD_LOCK:pass
    assert [r['id'] for r in node._fabric_media_catalog()['entries']]==['Berlin','new']


def test_unchanged_remote_revision_skips_full_transfer_and_changes_reload(tmp_path,monkeypatch):
    library=tmp_path/'library';library.write_text('{}')
    monkeypatch.setattr(node,'LOOK_MEDIA_LIBRARY',library)
    monkeypatch.setattr(node,'MEDIA_CATALOG_CACHE',{'data':None})
    monkeypatch.setattr(node,'MEDIA_PEER_CATALOGS',{})
    monkeypatch.setattr(node,'_refresh_media_peers_background',lambda:None)
    monkeypatch.setattr(node,'node_info',lambda:{})
    monkeypatch.setattr(node,'_local_media_catalog',lambda:{'node':'local','entries':[]})
    monkeypatch.setattr(node.PEERS,'public',lambda:[{'name':'owner','trusted':True,'node':{'identity':{'name':'owner'}},'url':'https://owner'}])
    revision=['one'];calls=[]
    def peer(peer,path,**kw):
        calls.append(path)
        return {'revision':revision[0]} if path.endswith('/revision') else {'revision':revision[0],'entries':[{'id':revision[0]}]}
    monkeypatch.setattr(node,'_peer_json',peer)
    assert node._fabric_media_catalog(force=True)['entries'][0]['id']=='one'
    assert node._fabric_media_catalog(force=True)['entries'][0]['id']=='one'
    assert calls==['/v1/media/catalog','/v1/media/catalog/revision']
    revision[0]='two'
    assert node._fabric_media_catalog(force=True)['entries'][0]['id']=='two'
    assert calls[-2:]==['/v1/media/catalog/revision','/v1/media/catalog']


def test_legacy_remote_without_revision_still_refreshes(tmp_path,monkeypatch):
    library=tmp_path/'library';library.write_text('{}')
    monkeypatch.setattr(node,'LOOK_MEDIA_LIBRARY',library)
    monkeypatch.setattr(node,'MEDIA_CATALOG_CACHE',{'data':None})
    monkeypatch.setattr(node,'MEDIA_PEER_CATALOGS',{'old':{'entries':[{'id':'old'}]}})
    monkeypatch.setattr(node,'_refresh_media_peers_background',lambda:None)
    monkeypatch.setattr(node,'node_info',lambda:{})
    monkeypatch.setattr(node,'_local_media_catalog',lambda:{'node':'local','entries':[]})
    monkeypatch.setattr(node.PEERS,'public',lambda:[{'name':'old','trusted':True,'node':{'identity':{'name':'old'}},'url':'https://old'}])
    def peer(peer,path,**kw):
        if path.endswith('/revision'):raise RuntimeError('404')
        return {'entries':[{'id':'new'}]}
    monkeypatch.setattr(node,'_peer_json',peer)
    assert node._fabric_media_catalog(force=True)['entries'][0]['id']=='new'


def test_refreshing_terminal_snapshot_is_rechecked_promptly(lk,monkeypatch,tmp_path):
    import io,json
    monkeypatch.setattr(lk,'HOME',tmp_path)
    path=tmp_path/'.cache/look/fabric-media-catalog.json';path.parent.mkdir(parents=True)
    path.write_text(json.dumps({'entries':[], 'refreshing':True,'_look_cached_at':time.time()-4,'_look_local_mtime_ns':-1}))
    fresh={'entries':[{'id':'Berlin'}],'nodes':[{'node':'local'}]}
    def request(*a,**kw):
        response=io.BytesIO(json.dumps(fresh).encode());response.headers={};return response
    monkeypatch.setattr(lk.urllib.request,'urlopen',request)
    assert lk._media_fabric_catalog()['entries']==fresh['entries']


def test_revision_endpoint_is_small_and_does_not_build_catalog(tmp_path,monkeypatch):
    import json,urllib.request
    library=tmp_path/'media_library.json';library.write_text('{}')
    monkeypatch.setattr(node,'LOOK_MEDIA_LIBRARY',library)
    monkeypatch.setattr(node,'identity',lambda:{'name':'owner'})
    monkeypatch.setattr(node,'_build_local_media_catalog',lambda:(_ for _ in ()).throw(AssertionError('expensive build')))
    server=node.FabricHTTPServer(('127.0.0.1',0),node.API,plane='local')
    threading.Thread(target=server.serve_forever,daemon=True).start()
    try:
        with urllib.request.urlopen(f'http://127.0.0.1:{server.server_port}/v1/media/catalog/revision',timeout=2) as response:
            data=response.read()
        value=json.loads(data)
        assert value=={'node':'owner','revision':node._local_media_catalog_revision()}
        assert len(data)<256
    finally:server.shutdown();server.server_close()
