from pathlib import Path
import importlib.machinery
import importlib.util
import json
import sys
import threading
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

ROOT=Path(__file__).resolve().parents[1]


def _load_node():
    core=ROOT/'core'
    sys.path.insert(0,str(core))
    name='fcl_node_778_test'
    spec=importlib.util.spec_from_file_location(name,core/'node.py')
    mod=importlib.util.module_from_spec(spec)
    sys.modules[name]=mod
    spec.loader.exec_module(mod)
    return mod


def _load_lk():
    name='look_lk_778_test'
    loader=importlib.machinery.SourceFileLoader(name,str(ROOT/'look/lk'))
    spec=importlib.util.spec_from_loader(name,loader)
    mod=importlib.util.module_from_spec(spec)
    sys.modules[name]=mod
    loader.exec_module(mod)
    return mod


def test_transport_owner_signature_executes_both_modes(monkeypatch):
    lk=_load_lk()
    monkeypatch.setattr(lk.platform,'system',lambda:'Darwin')
    seen=[]
    monkeypatch.setattr(lk,'_media_macos_owner',lambda *,include_paused_owner=True: seen.append(include_paused_owner) or None)
    assert lk._media_system_owner(include_paused_owner=False) is None
    assert lk._media_system_owner(include_paused_owner=True) is None
    assert seen == [False, True]


def test_catalog_path_hint_repairs_old_cheap_id_without_opening_arbitrary_file(tmp_path,monkeypatch):
    node=_load_node()
    media=tmp_path/'Talking Heads'/'Album'/'Wild Wild Life.mp3'
    media.parent.mkdir(parents=True); media.write_bytes(b'abc123')
    outside=tmp_path/'secret.txt'; outside.write_text('nope')
    library=tmp_path/'media_library.json'
    library.write_text(json.dumps({'entries':[{'id':'new-id','path':str(media),'media_type':'audio/mpeg'}]}))
    monkeypatch.setattr(node,'LOOK_MEDIA_LIBRARY',library)
    row,path=node._local_media_entry('old-id',str(media))
    assert row['id']=='new-id' and path==media
    try:
        node._local_media_entry('old-id',str(outside))
    except FileNotFoundError:
        pass
    else:
        raise AssertionError('path fallback escaped the scanned catalog')


def test_canonical_audio_route_proxies_catalog_identity_and_range(monkeypatch):
    node=_load_node()
    payload=b'0123456789abcdef'
    seen={}
    class Remote(BaseHTTPRequestHandler):
        def log_message(self,*args): pass
        def do_GET(self):
            seen['path']=self.path
            seen['range']=self.headers.get('Range')
            body=payload[4:10]
            self.send_response(206)
            self.send_header('Content-Type','audio/mpeg')
            self.send_header('Accept-Ranges','bytes')
            self.send_header('Content-Range',f'bytes 4-9/{len(payload)}')
            self.send_header('Content-Length',str(len(body)))
            self.end_headers(); self.wfile.write(body)
    remote=ThreadingHTTPServer(('127.0.0.1',0),Remote)
    tr=threading.Thread(target=remote.serve_forever,daemon=True); tr.start()
    monkeypatch.setattr(node,'identity',lambda:{'name':'mac'})
    monkeypatch.setattr(node.PEERS,'public',lambda:[])
    monkeypatch.setattr(node,'node_info',lambda:{})
    monkeypatch.setattr(node,'_peer_for_target',lambda snapshot,target:{'name':target})
    monkeypatch.setattr(node,'_peer_bases',lambda peer:[f'http://127.0.0.1:{remote.server_port}'])
    monkeypatch.setattr(node.FABRIC_IDENTITY,'auth_headers_for_url',lambda url:{})
    monkeypatch.setattr(node.FABRIC_IDENTITY,'ssl_context_for_url',lambda url:None)
    local=node.FabricHTTPServer(('127.0.0.1',0),node.API,plane='local')
    tl=threading.Thread(target=local.serve_forever,daemon=True); tl.start()
    try:
        url=(f'http://127.0.0.1:{local.server_port}/v1/media/audio?'
             'node=3090&id=old-id&path=%2Fmedia%2FTalking%20Heads.mp3')
        req=urllib.request.Request(url,headers={'Range':'bytes=4-9'})
        with urllib.request.urlopen(req,timeout=2) as response:
            assert response.status==206
            assert response.headers['Content-Range']==f'bytes 4-9/{len(payload)}'
            assert response.read()==b'456789'
        assert seen['range']=='bytes=4-9'
        assert seen['path'].startswith('/v1/media/audio?')
        assert 'id=old-id' in seen['path']
        assert 'path=%2Fmedia%2FTalking+Heads.mp3' in seen['path']
    finally:
        local.shutdown(); remote.shutdown(); local.server_close(); remote.server_close()


def test_signal_and_look_share_canonical_audio_edge():
    lk=(ROOT/'look/lk').read_text()
    signal=(ROOT/'signal-window/server.py').read_text()
    js=(ROOT/'signal-window/app.js').read_text()
    block=lk[lk.index('def _media_entry_source'):lk.index('def _media_wait_for_local_queue')]
    assert '/v1/media/audio?' in block
    assert '/v1/media/item?' not in block
    assert 'path' in block
    proxy=signal[signal.index('def _proxy_media_audio'):signal.index('_PRESENTED =')]
    assert 'path="/v1/media/audio"' in proxy
    assert '/v1/media/item' not in proxy
    assert "const itemPath=String(entry.path||'')" in js
