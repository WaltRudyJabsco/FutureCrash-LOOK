from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
NODE=(ROOT/'core'/'node.py').read_text(encoding='utf-8')


def test_browser_representation_transcodes_unsupported_audio():
    assert 'browser media conversion needs ffmpeg on the source node' in NODE
    assert '"-vn","-c:a","aac","-b:a","192k"' in NODE
    assert 'return target,"audio/mp4"' in NODE
    assert 'if is_audio and source.suffix.casefold() in {".mp3",".m4a",".aac",".wav"}' in NODE


def test_browser_representation_does_not_silently_fallback_to_original():
    block=NODE[NODE.index('def _serve_media_item'):NODE.index('def _serve_media_terminal_preview')]
    assert 'source,ctype=self._browser_media_source(entry_id,path_hint)' in block
    assert 'Delivery must not fail merely because ffmpeg is absent' not in block


def test_vision_route_preserves_meaningful_http_failure_before_tls_fallback():
    block=NODE[NODE.index('def _serve_vision_screen'):NODE.index('def _serve_vision_displays')]
    assert 'failures.append((0,base,f"HTTP {exc.code}' in block
    assert 'failures.append((3,base,f"TLS certificate verification failed' in block
    assert 'failures.sort(key=lambda row:row[0])' in block
    assert 'routes:' in block
