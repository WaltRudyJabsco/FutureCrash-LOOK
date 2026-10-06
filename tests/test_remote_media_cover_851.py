from pathlib import Path
from look import media_art

ROOT=Path(__file__).resolve().parents[1]
NODE=(ROOT/'core/node.py').read_text()
INGRESS=(ROOT/'core/ingress.py').read_text()
LK=(ROOT/'look/lk').read_text()


def test_fabric_exposes_dedicated_cover_route_without_media_download():
    assert 'def _serve_media_cover(self,target,entry_id,path_hint="",*,head=False):' in NODE
    assert 'url=base+"/v1/media/cover?"' in NODE
    assert 'return self._serve_media_cover(target,entry_id,path_hint' in NODE
    assert '"/v1/media/cover"' in INGRESS


def test_remote_cover_is_bounded_cached_and_renderer_fallback():
    start=LK.index('def _media_remote_cover_path')
    end=LK.index('def _media_cover_path',start)
    block=LK[start:end]
    assert "2*1024*1024+1" in block
    assert 'timeout=10.0' in block
    assert "media-art'/'remote'" in block
    assert '_REMOTE_MEDIA_ART_MISS' in block
    cover=LK[LK.index('def _media_cover_lines'):LK.index('def _media_player_art_lines')]
    assert '_media_remote_cover_path(row)' in cover
    assert 'media_art.symbol_lines(remote,width,height)' in cover


def test_direct_cached_image_is_valid_artwork(tmp_path):
    image=tmp_path/'remote-cover.jpg'
    image.write_bytes(b'fake-image-bytes')
    assert media_art.artwork_for(image)==image
