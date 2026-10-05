from pathlib import Path
import tempfile
from look import media_art


def test_sidecar_art_fallback():
    with tempfile.TemporaryDirectory() as td:
        root=Path(td); song=root/"song.m4a"; song.write_bytes(b"not-media")
        cover=root/"cover.jpg"; cover.write_bytes(b"jpg")
        old=media_art.shutil.which
        media_art.shutil.which=lambda name: None if name=="ffmpeg" else old(name)
        try: assert media_art.artwork_for(song)==cover
        finally: media_art.shutil.which=old

def test_audio_suffixes_include_apple_m4a():
    assert ".m4a" in media_art.AUDIO_SUFFIXES
