from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
NODE=(ROOT/'core'/'node.py').read_text(encoding='utf-8')


def test_browser_representation_transcodes_unsupported_audio(monkeypatch,tmp_path):
    from core import node
    from types import SimpleNamespace
    source=tmp_path/'track.flac';source.write_bytes(b'lossless original')
    monkeypatch.setattr(node.Path,'home',lambda:tmp_path)
    monkeypatch.setattr(node,'_local_media_entry',lambda *a:({'media_type':'audio/flac'},source))
    monkeypatch.setattr(node.shutil,'which',lambda name:'/tools/'+name)
    calls=[]
    def run(command,**kwargs):
        calls.append(command);Path(command[-1]).write_bytes(b'AAC')
        return SimpleNamespace(returncode=0)
    monkeypatch.setattr(node.subprocess,'run',run)
    target,kind=object.__new__(node.API)._browser_media_source('track')
    assert kind=='audio/mp4' and target!=source and source.read_bytes()==b'lossless original'
    assert calls[0][calls[0].index('-c:a')+1]=='aac'
    assert calls[0][calls[0].index('-b:a')+1]=='192k'


def test_browser_representation_does_not_silently_fallback_to_original(monkeypatch,tmp_path):
    import pytest
    from core import node
    source=tmp_path/'track.flac';source.write_bytes(b'original')
    monkeypatch.setattr(node,'_local_media_entry',lambda *a:({'media_type':'audio/flac'},source))
    monkeypatch.setattr(node.shutil,'which',lambda name:None)
    monkeypatch.setattr(node.os,'access',lambda *a:False)
    with pytest.raises(RuntimeError,match='needs ffmpeg'):
        object.__new__(node.API)._browser_media_source('track')


def test_vision_route_preserves_meaningful_http_failure_before_tls_fallback():
    block=NODE[NODE.index('def _serve_vision_screen'):NODE.index('def _serve_vision_displays')]
    assert 'failures.append((0,base,f"HTTP {exc.code}' in block
    assert 'failures.append((3,base,f"TLS certificate verification failed' in block
    assert 'failures.sort(key=lambda row:row[0])' in block
    assert 'routes:' in block
