from pathlib import Path
import subprocess, tempfile, os
from look import media_art


def _fixture(root: Path):
    cover=root/'cover.jpg'
    audio=root/'tone.m4a'
    # Produce a tiny deterministic cover and an M4A with it attached as cover art.
    subprocess.run(['ffmpeg','-nostdin','-loglevel','error','-f','lavfi','-i','color=c=gray:s=64x64','-frames:v','1','-y',str(cover)],check=True)
    subprocess.run(['ffmpeg','-nostdin','-loglevel','error','-f','lavfi','-i','sine=frequency=440:duration=0.25','-i',str(cover),
                    '-map','0:a','-map','1:v','-c:a','aac','-c:v','mjpeg','-disposition:v','attached_pic','-y',str(audio)],check=True)
    cover.unlink()
    return audio


def test_embedded_cover_extracts_and_player_ascii_needs_no_chafa(monkeypatch):
    with tempfile.TemporaryDirectory() as td:
        monkeypatch.setenv('HOME',td)
        song=_fixture(Path(td))
        art=media_art.artwork_for(song)
        assert art and art.is_file() and art.stat().st_size > 0
        real=media_art.shutil.which
        monkeypatch.setattr(media_art.shutil,'which',lambda name: None if name=='chafa' else real(name))
        lines=media_art.ascii_lines(song,16,6)
        assert media_art.symbol_lines(song,16,6) == lines
        assert len(lines)>=3
        assert all(set(line) <= set(' .:-=+*#%@') for line in lines)


def test_failed_extract_does_not_write_permanent_negative_cache(monkeypatch):
    with tempfile.TemporaryDirectory() as td:
        monkeypatch.setenv('HOME',td)
        song=Path(td)/'bad.m4a'; song.write_bytes(b'not media')
        assert media_art.artwork_for(song) is None
        cache=Path(td)/'.cache/look/media-art'
        assert not list(cache.glob('*.none'))
