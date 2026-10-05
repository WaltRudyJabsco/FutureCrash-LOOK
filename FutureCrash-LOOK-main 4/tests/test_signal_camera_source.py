import base64
import importlib.util
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]


def _signal_server():
    path=ROOT/"signal-window"/"server.py"
    spec=importlib.util.spec_from_file_location("signal_server_test",path)
    mod=importlib.util.module_from_spec(spec)
    assert spec.loader
    spec.loader.exec_module(mod)
    return mod


def test_camera_attachment_materializes_binary_bytes(tmp_path):
    mod=_signal_server()
    raw=b"\xff\xd8camera-bytes\xff\xd9"
    paths,notes=mod.materialize_files([{
        "name":"camera.jpg","type":"image/jpeg","encoding":"base64",
        "content":base64.b64encode(raw).decode("ascii"),"size":len(raw),
    }],tmp_path)
    assert Path(paths[0]).read_bytes()==raw
    assert "camera.jpg" in notes[0]


def test_signal_camera_surface_uses_native_capture_and_generic_chat_attachment():
    html=(ROOT/"signal-window"/"index.html").read_text()
    js=(ROOT/"signal-window"/"app.js").read_text()
    assert 'capture="environment"' in html
    assert 'accept="image/*"' in html
    assert "imageBase64" in js
    assert "CAMERA · PHOTO ATTACHED" in js
    assert "what am I looking at?" in js


def test_media_player_discovery_has_service_safe_paths():
    source=(ROOT/"look"/"lk").read_text()
    assert "/home/linuxbrew/.linuxbrew/bin/mpv" in source
    assert "/opt/homebrew/bin/mpv" in source
    assert "edge_log=io.StringIO()" in source
