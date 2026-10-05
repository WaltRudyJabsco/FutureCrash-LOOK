from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def test_albert_destroys_media_before_dom_replacement():
    text=(ROOT/'albert/index.html').read_text()
    assert "function teardownMedia(root=stream)" in text
    assert "media.pause()" in text
    assert "media.removeAttribute('src');media.load()" in text
    assert "AUDIO_EQ.delete(media)" in text
    assert "function render(){teardownMedia(stream);" in text
    assert "if(el)teardownMedia(el);f.dismissed=true" in text

def test_saved_surface_never_renders_media_player():
    text=(ROOT/'albert/index.html').read_text()
    block=text[text.index('function savedShell'):text.index('function teardownMedia')]
    assert '<audio' not in block
    assert '<video' not in block
    assert '<iframe' not in block
