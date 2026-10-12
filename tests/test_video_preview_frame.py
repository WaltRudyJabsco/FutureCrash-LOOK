from pathlib import Path
from types import SimpleNamespace
import shutil,subprocess
import pytest
from look import media_art as art


@pytest.mark.parametrize('duration,expected',[(7200,60),(30,6),(2,.4),(None,60),('bad',60),(float('inf'),60)])
def test_preview_uses_one_minute_or_earlier_for_short_clips(duration,expected):
    assert art.video_preview_second(duration)==expected


def test_seek_precedes_input_and_cache_avoids_repeated_probes(monkeypatch,tmp_path):
    source=tmp_path/'movie.mkv';source.write_bytes(b'original')
    monkeypatch.setattr(art.Path,'home',lambda:tmp_path)
    calls=[]
    def run(cmd,**kwargs):
        calls.append(cmd)
        if cmd[0]=='probe':return SimpleNamespace(stdout='120',returncode=0)
        Path(cmd[-1]).write_bytes(b'frame');return SimpleNamespace(returncode=0)
    monkeypatch.setattr(art.subprocess,'run',run)
    result=art.video_frame(source,ffmpeg='encoder',ffprobe='probe')
    assert calls[-1].index('-ss')<calls[-1].index('-i')
    assert calls[-1][calls[-1].index('-ss')+1]=='24.0'
    assert art.video_frame(source,ffmpeg='encoder',ffprobe='probe')==result and len(calls)==2
    assert source.read_bytes()==b'original'


def test_unknown_short_duration_falls_back_if_one_minute_has_no_frame(monkeypatch,tmp_path):
    source=tmp_path/'clip.mp4';source.write_bytes(b'original')
    monkeypatch.setattr(art.Path,'home',lambda:tmp_path)
    seeks=[]
    def run(cmd,**kwargs):
        if cmd[0]=='probe':return SimpleNamespace(stdout='N/A',returncode=0)
        seek=float(cmd[cmd.index('-ss')+1]);seeks.append(seek)
        if seek==0:Path(cmd[-1]).write_bytes(b'frame')
        return SimpleNamespace(returncode=0)
    monkeypatch.setattr(art.subprocess,'run',run)
    assert art.video_frame(source,ffmpeg='encoder',ffprobe='probe')
    assert seeks==[60,0]


@pytest.mark.skipif(not shutil.which('ffmpeg') or not shutil.which('ffprobe'),reason='FFmpeg tools required')
def test_real_short_video_preview_skips_black_opening(monkeypatch,tmp_path):
    source=tmp_path/'clip.mp4'
    subprocess.run(['ffmpeg','-v','error','-f','lavfi','-i','color=c=black:s=32x32:r=5:d=1','-f','lavfi','-i','color=c=red:s=32x32:r=5:d=5','-filter_complex','[0:v][1:v]concat=n=2:v=1:a=0','-c:v','libx264',str(source)],check=True,timeout=20)
    monkeypatch.setattr(art.Path,'home',lambda:tmp_path)
    frame=art.video_frame(source)
    pixels=subprocess.run(['ffmpeg','-v','error','-i',str(frame),'-f','rawvideo','-pix_fmt','rgb24','-'],check=True,capture_output=True,timeout=10).stdout
    assert sum(pixels[0::3])>sum(pixels[1::3])+1000
