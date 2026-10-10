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
