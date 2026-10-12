import json
import hashlib
import shutil
import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest
from core import node


@pytest.mark.parametrize('video,pixels,audio,expected',[
    ('h264','yuv420p','aac',('copy','copy')),
    ('h264','yuv420p','ac3',('copy','aac')),
    ('h264','yuv420p10le','aac',('libx264','aac')),
    ('mpeg2video','yuv420p','ac3',('libx264','aac')),
])
def test_browser_video_copies_supported_streams_and_caches(monkeypatch,tmp_path,video,pixels,audio,expected):
    source=tmp_path/'movie.mkv';source.write_bytes(b'original movie')
    monkeypatch.setattr(node.Path,'home',lambda:tmp_path)
    monkeypatch.setattr(node,'_local_media_entry',lambda *args:({'media_type':'video/matroska'},source))
    monkeypatch.setattr(node.shutil,'which',lambda name:'/tools/'+name)
    commands=[]
    def run(command,**kwargs):
        if 'ffprobe' in command[0]:
            return SimpleNamespace(stdout=json.dumps({'streams':[
                {'codec_type':'video','codec_name':video,'pix_fmt':pixels},
                {'codec_type':'audio','codec_name':audio}]}))
        commands.append(command);Path(command[-1]).write_bytes(b'browser movie')
        return SimpleNamespace(returncode=0,stdout='',stderr='')
    monkeypatch.setattr(node.subprocess,'run',run)
    handler=object.__new__(node.API)
    output,kind=handler._browser_media_source('movie')
    command=commands[0]
    assert (command[command.index('-c:v')+1],command[command.index('-c:a')+1])==expected
    assert ('-pix_fmt' in command)==(expected[0]!='copy')
    assert kind=='video/mp4' and output.read_bytes()==b'browser movie'
    assert source.read_bytes()==b'original movie'
    assert handler._browser_media_source('movie')[0]==output and len(commands)==1


def test_failed_remux_falls_back_to_encoder(monkeypatch,tmp_path):
    source=tmp_path/'movie.mkv';source.write_bytes(b'original')
    monkeypatch.setattr(node.Path,'home',lambda:tmp_path)
    monkeypatch.setattr(node,'_local_media_entry',lambda *args:({'media_type':'video/matroska'},source))
    monkeypatch.setattr(node.shutil,'which',lambda name:'/tools/'+name)
    commands=[]
    def run(command,**kwargs):
        if 'ffprobe' in command[0]:return SimpleNamespace(stdout=json.dumps({'streams':[{'codec_type':'video','codec_name':'h264','pix_fmt':'yuv420p'}]}))
        commands.append(command)
        if command[command.index('-c:v')+1]=='copy':return SimpleNamespace(returncode=1,stdout='',stderr='cannot remux')
        Path(command[-1]).write_bytes(b'converted')
        return SimpleNamespace(returncode=0,stdout='',stderr='')
    monkeypatch.setattr(node.subprocess,'run',run)
    output,kind=object.__new__(node.API)._browser_media_source('movie')
    assert len(commands)==2 and commands[1][commands[1].index('-c:v')+1]=='libx264'
    assert output.read_bytes()==b'converted' and source.read_bytes()==b'original'


@pytest.mark.skipif(not shutil.which('ffmpeg') or not shutil.which('ffprobe'),reason='requires FFmpeg tools')
def test_real_h264_remux_preserves_decoded_video_and_source(monkeypatch,tmp_path):
    source=tmp_path/'movie.mkv'
    subprocess.run(['ffmpeg','-v','error','-f','lavfi','-i','testsrc2=size=96x64:rate=12',
                    '-f','lavfi','-i','sine=frequency=400','-t','1','-c:v','libx264',
                    '-pix_fmt','yuv420p','-c:a','ac3',str(source)],check=True,timeout=20)
    original=hashlib.sha256(source.read_bytes()).hexdigest()
    monkeypatch.setattr(node.Path,'home',lambda:tmp_path)
    monkeypatch.setattr(node,'_local_media_entry',lambda *args:({'media_type':'video/matroska'},source))
    output,kind=object.__new__(node.API)._browser_media_source('movie')
    def hashes(path):
        result=subprocess.run(['ffmpeg','-v','error','-i',str(path),'-map','0:v:0','-f','framemd5','-'],capture_output=True,text=True,check=True,timeout=20)
        return [line.split(',')[-1].strip() for line in result.stdout.splitlines() if not line.startswith('#')]
    assert hashes(output)==hashes(source)
    assert hashlib.sha256(source.read_bytes()).hexdigest()==original
    probe=subprocess.run(['ffprobe','-v','error','-show_entries','stream=codec_name','-of','json',str(output)],capture_output=True,text=True,check=True,timeout=10)
    assert [row['codec_name'] for row in json.loads(probe.stdout)['streams']]==['h264','aac']
