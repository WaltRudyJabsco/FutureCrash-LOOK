from pathlib import Path
import importlib.util

ROOT=Path(__file__).resolve().parents[1]
MEDIA_CORE=(ROOT/'look/media_core.py').read_text()
LK=(ROOT/'look/lk').read_text()


def test_queue_preserves_remote_art_identity():
    assert 'out["art"]=chosen' in MEDIA_CORE
    assert 'candidates.append(dict(art))' in LK


def test_player_clips_art_by_visible_width():
    assert 'def _ansi_clip(text,width):' in LK
    block=LK[LK.index('def _media_player_render'):LK.index('def media_player')]
    assert '_ansi_clip(art[i] if i<len(art) else "",art_w)' in block
