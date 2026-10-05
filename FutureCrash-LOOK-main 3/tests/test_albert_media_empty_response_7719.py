import importlib.util
import threading
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

def _load_albert():
    path = Path(__file__).resolve().parents[1] / "albert" / "server.py"
    spec = importlib.util.spec_from_file_location("albert_media_7719", path)
    mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod); return mod

def test_ticketed_range_media_request_returns_audio_not_empty_response():
    albert = _load_albert(); payload = b"ID3" + (b"x" * 1021)
    class Upstream(BaseHTTPRequestHandler):
        def log_message(self, *_args): pass
        def do_GET(self):
            assert self.path == "/v1/media/item?node=3090&id=item123"
            assert self.headers.get("Range") == "bytes=0-"
            self.send_response(206); self.send_header("Content-Type", "audio/mpeg"); self.send_header("Content-Length", str(len(payload))); self.send_header("Content-Range", f"bytes 0-{len(payload)-1}/{len(payload)}"); self.send_header("Accept-Ranges", "bytes"); self.end_headers(); self.wfile.write(payload)
    upstream = ThreadingHTTPServer(("127.0.0.1", 0), Upstream); browser_edge = ThreadingHTTPServer(("127.0.0.1", 0), albert.Handler)
    threading.Thread(target=upstream.serve_forever, daemon=True).start(); threading.Thread(target=browser_edge.serve_forever, daemon=True).start(); old_node = albert.NODE
    try:
        albert.NODE = f"http://127.0.0.1:{upstream.server_port}"; ticket = albert._media_ticket_issue("3090", "item123")
        url = f"http://127.0.0.1:{browser_edge.server_port}/api/media/audio?node=3090&id=item123&ticket={ticket}"
        request = urllib.request.Request(url, headers={"Range": "bytes=0-"})
        with urllib.request.urlopen(request, timeout=3) as response:
            assert response.status == 206; assert response.headers["Content-Type"] == "audio/mpeg"; assert response.headers["Accept-Ranges"] == "bytes"; assert response.headers["Content-Range"] == f"bytes 0-{len(payload)-1}/{len(payload)}"; assert response.read() == payload
    finally:
        albert.NODE = old_node; browser_edge.shutdown(); upstream.shutdown()
