from pathlib import Path
import importlib.util
import sys

ROOT=Path(__file__).resolve().parents[1]
LK=(ROOT/'look/lk').read_text()
RENDER=(ROOT/'look/look_renderer.py').read_text()
sys.path.insert(0,str(ROOT/'core'))

spec=importlib.util.spec_from_file_location('fcl_ingress',ROOT/'core/ingress.py')
ingress=importlib.util.module_from_spec(spec); spec.loader.exec_module(ingress)


def test_ingress_streams_media_bytes_instead_of_buffering_control_response():
    for path in ('/v1/media/item','/v1/media/audio','/v1/media/artifact','/v1/artifacts/sha256:abc'):
        assert ingress._is_stream_path(path)
    assert not ingress._is_stream_path('/v1/media/state')
    assert 'STREAM_TIMEOUT_SECONDS if is_stream else CONTROL_TIMEOUT_SECONDS' in (ROOT/'core/ingress.py').read_text()


def test_ingress_preserves_content_length_for_stream_and_range_headers():
    src=(ROOT/'core/ingress.py').read_text()
    assert 'if lk == "content-length" and not is_stream' in src
    assert 'headers[key] = value' in src  # Range request header survives to backend.


def test_linux_jpeg_first_frame_selector_is_attached_to_input_filename():
    assert "str(path)+'[0]'" in RENDER
    assert "str(path),'[0]'" not in RENDER


def test_transport_shortcuts_keep_human_grammar():
    z=(ROOT/'look/zshrc').read_text()
    assert "alias mm='lk media toggle'" in z
    assert "alias mn='lk media next'" in z
    assert "alias mp='lk media prev'" in z


def test_transport_uses_single_active_owner_before_saved_look_queue():
    assert 'system_owner=_media_system_owner()' in LK
    assert 'if system_owner:' in LK
    assert 'return _media_system_control(action,system_owner)' in LK
    assert 'session["owner"]="look"' in LK
    assert '_media_claim_owner("system:"+app)' in LK
    assert '_media_claim_owner("system:"+chosen)' in LK


def test_pause_and_play_are_not_mapped_to_toggle_for_system_players():
    assert '"Music":{"play":"play","pause":"pause","toggle":"playpause"' in LK
    assert '"play":"play","pause":"pause","toggle":"play-pause"' in LK
    assert 'legacy_action=' not in LK


def test_media_state_exposes_owner_and_source_playback_nodes():
    assert '"owner":str(session.get("owner") or "")' in LK
    assert '"source_node":str((snap.get("entry") or {}).get("node") or "")' in LK
    assert '"playback_node":socket.gethostname()' in LK

def test_ingress_media_item_range_round_trip(monkeypatch):
    import threading, urllib.request
    from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

    payload=b'0123456789abcdef'
    class Backend(BaseHTTPRequestHandler):
        def log_message(self,*args): pass
        def do_GET(self):
            assert self.path.startswith('/v1/media/item')
            assert self.headers.get('Range')=='bytes=4-9'
            body=payload[4:10]
            self.send_response(206)
            self.send_header('Content-Type','audio/mpeg')
            self.send_header('Accept-Ranges','bytes')
            self.send_header('Content-Range',f'bytes 4-9/{len(payload)}')
            self.send_header('Content-Length',str(len(body)))
            self.end_headers(); self.wfile.write(body)

    backend=ThreadingHTTPServer(('127.0.0.1',0),Backend)
    guard=ingress.GuardServer(('127.0.0.1',0),ingress.Handler,'127.0.0.1',backend.server_port)
    monkeypatch.setattr(ingress.FABRIC_IDENTITY,'verify_peer',lambda node,token: True)
    tb=threading.Thread(target=backend.serve_forever,daemon=True); tb.start()
    tg=threading.Thread(target=guard.serve_forever,daemon=True); tg.start()
    try:
        req=urllib.request.Request(
            f'http://127.0.0.1:{guard.server_port}/v1/media/item?id=test',
            headers={'Range':'bytes=4-9','X-Fabric-Node':'peer','Authorization':'Bearer test'})
        with urllib.request.urlopen(req,timeout=2) as response:
            assert response.status==206
            assert response.headers['Content-Range']==f'bytes 4-9/{len(payload)}'
            assert response.headers['Content-Length']=='6'
            assert response.read()==b'456789'
    finally:
        guard.shutdown(); backend.shutdown(); guard.server_close(); backend.server_close()
