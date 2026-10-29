"""Owner-side standard audio leaves masters and logical identities intact."""
import hashlib
import json
import shutil
import subprocess
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from types import SimpleNamespace
from urllib.parse import parse_qs,urlparse

import pytest
from core import node
from look import player_visuals
from test_media_request_regressions import lk


@pytest.mark.parametrize('suffix',['.flac','.wav','.aiff','.alac'])
def test_standard_audio_shared_cache_and_invalidation(monkeypatch,tmp_path,suffix):
    source=tmp_path/('master'+suffix);source.write_bytes(b'lossless master')
    monkeypatch.setattr(node.Path,'home',lambda:tmp_path)
    monkeypatch.setattr(node,'_local_media_entry',lambda *a:({'media_type':'audio/flac'},source))
    monkeypatch.setattr(node.shutil,'which',lambda name:'/tools/'+name)
    calls=[]
    def encode(command,**kw):
        calls.append(command);Path(command[-1]).write_bytes(b'cached AAC')
        return SimpleNamespace(returncode=0,stderr='')
    monkeypatch.setattr(node.subprocess,'run',encode)
    handler=object.__new__(node.API)
    def standard(_):return handler._browser_media_source('track',audio_delivery=True)
    with ThreadPoolExecutor(max_workers=2) as pool:outputs=list(pool.map(standard,range(2)))
    assert outputs[0]==outputs[1] and len(calls)==1
    assert calls[0][calls[0].index('-b:a')+1]=='192k'
    assert source.read_bytes()==b'lossless master'
    assert outputs[0][1]=='audio/mp4'
    assert handler._browser_media_source('track')==outputs[0]
    source.write_bytes(b'changed lossless master')
    assert standard(0)[0]!=outputs[0][0] and len(calls)==2


@pytest.mark.parametrize('suffix,codec',[('.mp3','mp3'),('.aac','aac'),('.ogg','vorbis'),('.m4a','aac'),('.m4b','aac')])
def test_existing_lossy_audio_is_not_encoded(monkeypatch,tmp_path,suffix,codec):
    source=tmp_path/('track'+suffix);source.write_bytes(b'existing compressed audio')
    monkeypatch.setattr(node,'_local_media_entry',lambda *a:({'media_type':'audio/mpeg'},source))
    monkeypatch.setattr(node.shutil,'which',lambda name:'/tools/'+name)
    def probe(command,**kw):
        assert 'ffprobe' in command[0]
        return SimpleNamespace(stdout=json.dumps({'streams':[{'codec_name':codec}]}))
    monkeypatch.setattr(node.subprocess,'run',probe)
    assert object.__new__(node.API)._browser_media_source('track',audio_delivery=True)[0]==source


def test_failed_conversion_cleans_staging_and_keeps_master(monkeypatch,tmp_path):
    source=tmp_path/'master.flac';source.write_bytes(b'master')
    monkeypatch.setattr(node.Path,'home',lambda:tmp_path)
    monkeypatch.setattr(node,'_local_media_entry',lambda *a:({'media_type':'audio/flac'},source))
    monkeypatch.setattr(node.shutil,'which',lambda name:'/tools/'+name)
    def fail(command,**kw):
        Path(command[-1]).write_bytes(b'partial')
        raise subprocess.TimeoutExpired(command,900)
    monkeypatch.setattr(node.subprocess,'run',fail)
    with pytest.raises(subprocess.TimeoutExpired):object.__new__(node.API)._browser_media_source('track',audio_delivery=True)
    assert source.read_bytes()==b'master' and not list(tmp_path.rglob('*.m4a'))


def test_terminal_routes_standard_remote_audio_but_original_local_and_video(lk,monkeypatch,tmp_path):
    monkeypatch.setattr(lk,'_media_local_node_names',lambda:{'local'})
    row={'node':'tower','id':'track','path':'/music/master.flac','media_type':'audio/flac'}
    query=parse_qs(urlparse(lk._media_entry_source(row)).query)
    assert query['representation']==['audio'] and query['id']==['track']
    assert 'representation' not in parse_qs(urlparse(lk._media_entry_source(row,standard_audio=False)).query)
    movie=dict(row,path='/movies/movie.mkv',media_type='video/matroska')
    assert 'representation' not in parse_qs(urlparse(lk._media_entry_source(movie)).query)
    source=tmp_path/'local.flac';source.write_bytes(b'master')
    assert lk._media_entry_source(dict(row,node='local',path=str(source)))==str(source)
    monkeypatch.setenv('LOOK_MEDIA_AUDIO_QUALITY','original')
    assert 'representation' not in parse_qs(urlparse(lk._media_entry_source(row)).query)


@pytest.mark.parametrize('name',['Magnetic Field','Comet Trails'])
def test_new_visuals_animate_pause_and_join_cycle(name):
    mode=player_visuals.NAMES.index(name)+1
    for w,h in [(1,1),(19,6),(100,30)]:
        frame=player_visuals.frame(mode,w,h,2,seed=7)
        assert len(frame)==h and all(len(line)==w for line in frame)
        assert all(ord(c)<128 for line in frame for c in line)
    assert player_visuals.frame(mode,80,20,2)!=player_visuals.frame(mode,80,20,7)
    assert player_visuals.frame(mode,80,20,2,False)==player_visuals.frame(mode,80,20,7,False)
    assert mode in {player_visuals.active_mode(player_visuals.CYCLE_MODE,i*10) for i in range(player_visuals.CYCLE_MODE-1)}


def test_real_lossless_to_aac_is_small_and_decodable(monkeypatch,tmp_path):
    ffmpeg=shutil.which('ffmpeg');ffprobe=shutil.which('ffprobe')
    if not ffmpeg or not ffprobe:pytest.skip('ffmpeg/ffprobe unavailable')
    source=tmp_path/'master.wav'
    subprocess.run([ffmpeg,'-v','error','-f','lavfi','-i','sine=frequency=440:duration=2','-ac','2',str(source)],check=True)
    before=hashlib.sha256(source.read_bytes()).hexdigest()
    monkeypatch.setattr(node.Path,'home',lambda:tmp_path)
    monkeypatch.setattr(node,'_local_media_entry',lambda *a:({'media_type':'audio/wav'},source))
    handler=object.__new__(node.API)
    target,kind=handler._browser_media_source('track',audio_delivery=True)
    streams=json.loads(subprocess.check_output([ffprobe,'-v','error','-show_streams','-of','json',str(target)]))['streams']
    assert streams[0]['codec_name']=='aac' and kind=='audio/mp4'
    assert target.stat().st_size<source.stat().st_size
    assert hashlib.sha256(source.read_bytes()).hexdigest()==before
    assert handler._browser_media_source('track',audio_delivery=True)[0]==target


def test_alac_inside_m4a_is_converted(monkeypatch,tmp_path):
    source=tmp_path/'lossless.m4a';source.write_bytes(b'ALAC master')
    monkeypatch.setattr(node.Path,'home',lambda:tmp_path)
    monkeypatch.setattr(node,'_local_media_entry',lambda *a:({'media_type':'audio/mp4'},source))
    monkeypatch.setattr(node.shutil,'which',lambda name:'/tools/'+name)
    def run(command,**kw):
        if 'ffprobe' in command[0]:return SimpleNamespace(stdout='{"streams":[{"codec_name":"alac"}]}')
        Path(command[-1]).write_bytes(b'AAC copy')
        return SimpleNamespace(returncode=0)
    monkeypatch.setattr(node.subprocess,'run',run)
    target,_=object.__new__(node.API)._browser_media_source('track',audio_delivery=True)
    assert target!=source and target.read_bytes()==b'AAC copy' and source.read_bytes()==b'ALAC master'


def test_proxy_preserves_audio_representation_and_range(monkeypatch):
    import io
    handler=object.__new__(node.API);handler.headers={'Range':'bytes=10-19'};handler.wfile=io.BytesIO()
    monkeypatch.setattr(node,'identity',lambda:{'name':'client'})
    monkeypatch.setattr(node,'node_info',lambda:{})
    monkeypatch.setattr(node.PEERS,'public',lambda:[])
    monkeypatch.setattr(node,'_peer_for_target',lambda *a:{})
    monkeypatch.setattr(node,'_file_race',lambda *a:('https://tower',{}))
    monkeypatch.setattr(node,'_peer_bases',lambda *a:['https://tower'])
    monkeypatch.setattr(node.FABRIC_IDENTITY,'auth_headers_for_url',lambda *a:{'Authorization':'paired'})
    monkeypatch.setattr(node.FABRIC_IDENTITY,'ssl_context_for_url',lambda *a:None)
    requests=[]
    class Response(io.BytesIO):
        status=206
        headers={'Content-Type':'audio/mp4','Content-Length':'10','Content-Range':'bytes 10-19/100','Accept-Ranges':'bytes'}
    def opened(req,**kw):
        requests.append(req)
        assert kw['timeout']>=90
        return Response(b'0123456789')
    monkeypatch.setattr(node.urllib.request,'urlopen',opened)
    statuses=[];headers={}
    monkeypatch.setattr(handler,'send_response',statuses.append)
    monkeypatch.setattr(handler,'send_header',lambda k,v:headers.update({k:v}))
    monkeypatch.setattr(handler,'end_headers',lambda:None)
    handler._serve_media_item('tower','track',representation='audio')
    assert parse_qs(urlparse(requests[0].full_url).query)['representation']==['audio']
    assert requests[0].get_header('Range')=='bytes=10-19'
    assert statuses==[206] and headers['Content-Range']=='bytes 10-19/100'
    assert handler.wfile.getvalue()==b'0123456789'


def test_cold_aac_start_waits_for_decoder_not_just_open_url(lk,monkeypatch):
    clock=[0.0]
    monkeypatch.setattr(lk.time,'monotonic',lambda:clock[0])
    monkeypatch.setattr(lk.time,'sleep',lambda _:clock.__setitem__(0,clock[0]+1))
    monkeypatch.setattr(lk,'_media_mpv_loaded',lambda:clock[0]>=15)
    monkeypatch.setattr(lk,'_media_mpv_property',lambda _: 'http://127.0.0.1:7332/v1/media/item?id=track&representation=audio')
    assert lk._media_wait_for_mpv_loaded() and clock[0]>=15
    clock[0]=0
    monkeypatch.setattr(lk,'_media_mpv_property',lambda _:'http://127.0.0.1:7332/v1/media/item?id=track')
    assert not lk._media_wait_for_mpv_loaded() and clock[0]==lk.MEDIA_SOURCE_STARTUP_SECONDS
