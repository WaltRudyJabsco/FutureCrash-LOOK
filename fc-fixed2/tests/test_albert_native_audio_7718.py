from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_albert_eq_never_rewires_audio_graph():
    html = (ROOT / "albert" / "index.html").read_text()
    assert "function initAudioEQ()" in html
    assert "eqFallback(audio,[...box.children])" in html
    assert "createMediaElementSource" not in html
    assert "new AudioContext" not in html


def test_albert_fabric_media_still_uses_ticketed_native_audio():
    html = (ROOT / "albert" / "index.html").read_text()
    server = (ROOT / "albert" / "server.py").read_text()
    assert "fetch('/api/media/ticket?'" in html
    assert "media.src=d.url" in html
    assert "media.load()" in html
    assert "await media.play()" in html
    assert "'/api/media/audio'" in server
    assert "_proxy_media_item(self,node,item_id" in server
