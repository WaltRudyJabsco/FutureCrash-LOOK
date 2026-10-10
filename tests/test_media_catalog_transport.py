import gzip
import json
import threading
import time
import urllib.request
from core import ingress,node


def test_catalog_json_is_compressed_and_streamed_without_control_deadline(monkeypatch):
    payload={'entries':[{'id':str(i),'path':'/Music/Artist/Album/Track.mp3','title':'Song'} for i in range(10000)]}
    def catalog():
        time.sleep(.06)
        return payload
    monkeypatch.setattr(node,'_local_media_catalog',catalog)
    monkeypatch.setattr(ingress.Handler,'_authorized',lambda self,path:True)
    monkeypatch.setattr(ingress,'CONTROL_TIMEOUT_SECONDS',.02)
    monkeypatch.setattr(ingress,'CATALOG_TIMEOUT_SECONDS',2)
    monkeypatch.setattr(ingress,'HEADER_TIMEOUT_SECONDS',.02)
    backend=node.FabricHTTPServer(('127.0.0.1',0),node.API,plane='local')
    proxy=ingress.GuardServer(('127.0.0.1',0),ingress.Handler,'127.0.0.1',backend.server_port)
    for server in (backend,proxy):threading.Thread(target=server.serve_forever,daemon=True).start()
    try:
        url=f'http://127.0.0.1:{proxy.server_port}/v1/media/catalog'
        request=urllib.request.Request(url,headers={'Accept-Encoding':'gzip'})
        with urllib.request.urlopen(request,timeout=3) as response:
            compressed=response.read()
            assert response.headers['Content-Encoding']=='gzip'
            assert int(response.headers['Content-Length'])==len(compressed)
        assert json.loads(gzip.decompress(compressed))==payload
        assert len(compressed)<len(json.dumps(payload).encode())/10
        assert node.http_json(url,timeout=3)==payload
        # Older clients still receive ordinary JSON.
        with urllib.request.urlopen(url,timeout=3) as response:
            assert response.headers.get('Content-Encoding') is None
            assert json.load(response)==payload
    finally:
        for server in (proxy,backend):server.shutdown();server.server_close()


def test_catalog_routes_are_incremental_streams():
    assert ingress._is_stream_path('/v1/media/catalog')
    assert ingress._is_stream_path('/v1/media/fabric')
    assert not ingress._is_stream_path('/v1/node')


def test_concurrent_local_catalog_readers_share_one_build_and_edits_invalidate(tmp_path,monkeypatch):
    import concurrent.futures
    library=tmp_path/'media_library.json';library.write_text('{}')
    visibility=tmp_path/'media_owner_visibility.json'
    monkeypatch.setattr(node,'LOOK_MEDIA_LIBRARY',library)
    monkeypatch.setattr(node,'identity',lambda:{'name':'owner'})
    monkeypatch.setattr(node,'LOCAL_MEDIA_CATALOG_CACHE',{'at':0,'data':None,'stamp':None})
    calls=[];clock=[100.0]
    monkeypatch.setattr(node,'now',lambda:clock[0])
    def build():
        calls.append(1);time.sleep(.03)
        return {'entries':[{'id':str(len(calls))}]}
    monkeypatch.setattr(node,'_build_local_media_catalog',build)
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        results=list(pool.map(lambda _:node._local_media_catalog(),range(4)))
    assert len(calls)==1 and all(result==results[0] for result in results)
    library.write_text('{"entries":[]}')
    assert node._local_media_catalog()['entries'][0]['id']=='2'
    visibility.write_text('{"paths":["/hidden.mp3"]}')
    assert node._local_media_catalog()['entries'][0]['id']=='3'
    clock[0]+=node.LOCAL_MEDIA_CATALOG_TTL_SECONDS+1
    assert node._local_media_catalog()['entries'][0]['id']=='4'
