import hashlib
import io
import json
import threading
import time
from pathlib import Path
from unittest.mock import Mock

import pytest
from core import fabric_client as client
import media_offline
from look import player_visuals
from test_media_request_regressions import lk
from test_future_crash_channels import load_fc


@pytest.fixture(autouse=True)
def clear_failed_peers():
    client._failed_peers.clear()
    yield
    client._failed_peers.clear()


def worker(name, size=2):
    return {'name':name,'inference':{'available':True,'models':[
        {'name':name,'resident':True,'size':size,'features':{'text':True,'tools':True}}]}}


def test_stale_peer_and_failed_peer_never_outrank_local():
    local=worker('laptop',20_000_000_000)
    for extra in ({'node_error':'offline'},{'node_seen_at':time.time()-1000}):
        snapshot={'self':local,'peers':[dict(name='tower',dns='tower.example',node=worker('tower'),**extra)]}
        assert client._choose_from_snapshot(snapshot,latency=True)[1]=='laptop'


def test_dead_remote_falls_back_to_different_capable_local_model(monkeypatch):
    snapshot={'self':worker('laptop',20_000_000_000),'peers':[
        {'name':'tower','dns':'tower.example','node':worker('tower')}]}
    monkeypatch.setattr(client,'_nodes',lambda _:snapshot)
    probes=[]
    def request(url,payload=None,timeout=5):
        if url.endswith('/health'):
            probes.append(timeout);raise TimeoutError('airplane')
        if url.endswith('/v1/jobs'):return {'job':{'id':'local-job'}}
        return {'status':'ok','result':{'work':{'output':{'message':{'content':'local reply'}}}}}
    monkeypatch.setattr(client,'_json',request)
    result=client.infer([{'role':'user','content':'hello'}],latency=True)
    assert result['fabric_node']=='laptop' and result['message']['content']=='local reply'
    assert probes==[client.PEER_PROBE_SECONDS]


def test_queued_inference_cancellation_posts_control(monkeypatch):
    cancelled=threading.Event();calls=[]
    monkeypatch.setattr(client,'_nodes',lambda _: {'self':worker('laptop')})
    def request(url,payload=None,timeout=5):
        calls.append((url,payload))
        if url.endswith('/v1/jobs'):
            cancelled.set();return {'job':{'id':'queued'}}
        return {}
    monkeypatch.setattr(client,'_json',request)
    with pytest.raises(InterruptedError):client.infer([],cancel_event=cancelled)
    assert calls[-1][0].endswith('/v1/jobs/queued/control')
    assert calls[-1][1]['operation']=='cancel'


def test_closing_stream_cancels_its_exact_job(monkeypatch):
    monkeypatch.setattr(client,'_nodes',lambda _: {'self':worker('laptop')})
    class Response:
        headers={}
        def __enter__(self):return self
        def __exit__(self,*_):pass
        def __iter__(self):yield b'{"message":{"content":"first"}}\n'
    packet=[];controls=[]
    def opened(req,**kw):packet.append(json.loads(req.data)['packet']);return Response()
    monkeypatch.setattr(client,'_open',opened)
    monkeypatch.setattr(client,'_json',lambda url,payload=None,**kw:controls.append((url,payload)))
    stream=client.stream_infer({'messages':[]})
    next(stream);next(stream);stream.close()
    assert controls[-1][0].endswith('/v1/jobs/'+packet[0]['id']+'/control')


def test_local_runtime_works_without_node_service(monkeypatch):
    def request(url,payload=None,timeout=5):
        if url.endswith('/v1/nodes'):raise OSError('node stopped')
        if url.endswith('/api/tags'):return {'models':[{'name':'small','size':200}]}
        if url.endswith('/api/ps'):return {'models':[{'name':'small'}]}
        if url.endswith('/api/show'):return {'capabilities':['completion','tools']}
        raise AssertionError(url)
    monkeypatch.setattr(client,'_json',request)
    snap=client._nodes(client.DEFAULT_NODE)
    assert snap['self']['direct_ollama']=='http://127.0.0.1:11434'
    assert client._choose_from_snapshot(snap,requires=['text','tools'])[1]=='local'
    events=iter([{'message':{'content':'off'}},{'message':{'content':'line'},'done':True}])
    monkeypatch.setattr(client,'_direct_stream',lambda *args:events)
    assert client.infer([])['message']['content']=='offline'


def test_timed_out_media_is_not_playable(lk,monkeypatch):
    monkeypatch.setattr(lk,'_media_local_node_names',lambda:{'local'})
    monkeypatch.setattr(lk.urllib.request,'urlopen',Mock(side_effect=TimeoutError('offline')))
    with pytest.raises(FileNotFoundError,match='no reachable'):
        lk._media_pin_playable_entry({'node':'remote','id':'track','path':'/song.mp3'})


class BytesResponse(io.BytesIO):
    status=200
    def __init__(self,data,total=None):
        super().__init__(data);self.headers={'Content-Length':str(len(data) if total is None else total)}


def source(data):
    return {'node':'owner','id':'track','path':'/music/song.mp3','digest':hashlib.sha256(data).hexdigest()}


def test_offline_copy_is_verified_and_reusable(monkeypatch,tmp_path):
    data=b'our audio'*100
    opened=Mock(side_effect=lambda *a,**k:BytesResponse(data))
    monkeypatch.setattr(media_offline.urllib.request,'urlopen',opened)
    progress=[]
    target=media_offline.keep(source(data),tmp_path,progress=lambda n,total:progress.append((n,total)))
    assert target.read_bytes()==data and progress[-1]==(len(data),len(data))
    assert media_offline.keep(source(data),tmp_path)==target
    assert opened.call_count==3 # HEAD, GET, HEAD for verified reuse
    availability=media_offline.Availability({'laptop'})
    try:
        row={'node':'owner','path':'/song.mp3','locations':[{'node':'laptop','path':str(target)}]}
        assert availability.state(row)=='local'
        target.unlink()
        assert availability.state(row)=='checking' # unplugged/removed copy is rechecked
    finally:availability.close()


@pytest.mark.parametrize('failure',['checksum','short','cancel'])
def test_failed_copy_never_publishes_partial_media(monkeypatch,tmp_path,failure):
    data=b'original'
    sent=b'damaged!' if failure=='checksum' else b'ori' if failure=='short' else data
    monkeypatch.setattr(media_offline.urllib.request,'urlopen',lambda *a,**k:BytesResponse(sent,len(data)))
    def progress(*_):
        if failure=='cancel':raise KeyboardInterrupt
    with pytest.raises((ValueError,KeyboardInterrupt)):
        media_offline.keep(source(data),tmp_path,progress=progress)
    assert not list(tmp_path.rglob('song.mp3')) and not list(tmp_path.rglob('.offline-*'))


def test_availability_has_no_catalog_wide_probe(monkeypatch):
    gate=threading.Event();calls=[]
    availability=media_offline.Availability({'local'})
    def probe(row):calls.append(row);gate.wait(2);return 'offline'
    monkeypatch.setattr(availability,'_probe',probe)
    rows=[{'node':'remote','id':str(i),'path':'/missing'} for i in range(160_000)]
    try:
        availability.poll(rows[:20])
        assert len(availability.pending)<=2
        gate.set()
        for future in list(availability.pending.values()):future.result(2)
        assert availability.poll([])
        assert availability.state(rows[0])=='offline'
        assert len(calls)==2
    finally:gate.set();availability.close()


def test_oracle_cancels_queue_and_discards_late_response():
    fc=load_fc();oracle=fc.Oracle('http://unreachable','model')
    oracle.ask('ask','first');generation=oracle.generation;token=oracle.cancel_event
    oracle.cancel()
    assert token.is_set() and oracle.requests.empty()
    oracle._respond(generation,('ask','late',None,{}))
    assert oracle.responses.empty()
    oracle.ask('ask','new')
    assert not oracle.cancel_event.is_set() and not oracle.requests.empty()


@pytest.mark.parametrize('name',['Aurora Loom','Paper Lanterns'])
def test_new_visuals_animate_pause_and_cycle(name):
    mode=player_visuals.NAMES.index(name)+1
    a=player_visuals.frame(mode,72,18,1,seed=13)
    assert len(a)==18 and all(len(line)==72 for line in a)
    assert a!=player_visuals.frame(mode,72,18,6,seed=13)
    assert player_visuals.frame(mode,72,18,1,False)==player_visuals.frame(mode,72,18,6,False)
    assert mode in {player_visuals.active_mode(player_visuals.CYCLE_MODE,i*10) for i in range(player_visuals.CYCLE_MODE-1)}


@pytest.mark.parametrize('surface',['find','audio','video'])
def test_keep_offline_shortcut_passes_selection_without_playing(lk,monkeypatch,surface):
    from test_media_desks_v2 import Terminal,Durations,Preview
    import os
    row={'node':'remote','id':'one','path':'/movie.mp4' if surface=='video' else '/song.mp3'}
    monkeypatch.setattr(lk.sys,'stdin',Terminal());monkeypatch.setattr(lk.sys,'stdout',Terminal())
    monkeypatch.setattr(lk.termios,'tcgetattr',lambda *_:[])
    monkeypatch.setattr(lk.termios,'tcsetattr',lambda *_:None)
    monkeypatch.setattr(lk.tty,'setcbreak',lambda *_:None)
    monkeypatch.setattr(lk,'_media_local_node_names',lambda:{'local'})
    monkeypatch.setattr(lk.shutil,'get_terminal_size',lambda *_:os.terminal_size((100,34)))
    monkeypatch.setattr(lk,'DurationPreview',Durations);monkeypatch.setattr(lk,'NativePreviewController',Preview)
    monkeypatch.setattr(lk,'_media_catalog_entries',lambda:([row],{}))
    monkeypatch.setattr(lk,'_media_visibility',lambda:{})
    monkeypatch.setattr(lk,'_media_is_hidden',lambda *a:False)
    monkeypatch.setattr(lk,'_media_status_snapshot',lambda:None)
    monkeypatch.setattr(lk,'_media_cover_lines',lambda *a,**kw:[])
    monkeypatch.setattr(lk,'_media_remote_preview_state',lambda *a:('unavailable',''))
    monkeypatch.setattr(lk,'_media_detail_lines',lambda *a:[])
    monkeypatch.setattr(media_offline.Availability,'poll',lambda *a:False)
    keys=iter(['Y','esc']);monkeypatch.setattr(lk,'_read_tty_key',lambda *a:next(keys))
    copies=[];monkeypatch.setattr(lk,'_media_keep_offline',lambda rows,*a:copies.append(rows) or 'copied')
    monkeypatch.setattr(lk,'_media_launch_session',lambda *a:pytest.fail('copy must not play'))
    if surface=='find':lk._media_selector([row])
    else:lk._media_player_library(media_kind=surface)
    assert copies and copies[0][0]['id']=='one'


def test_keep_offline_indexes_metadata_and_updates_saved_queue(lk,monkeypatch,tmp_path):
    row=dict(source(b'audio'),title='Song',artist='Artist',album='Album',bytes=5)
    target=tmp_path/'travel/music/song.mp3';target.parent.mkdir(parents=True);target.write_bytes(b'audio')
    monkeypatch.setattr(lk,'HOME',tmp_path)
    monkeypatch.setattr(lk,'MEDIA_LIBRARY_FILE',tmp_path/'library.json')
    monkeypatch.setattr(lk,'_media_local_node_names',lambda:{'local'})
    monkeypatch.setattr(lk.platform,'node',lambda:'laptop')
    session={'queue':[dict(row)]};monkeypatch.setattr(lk,'_media_session',lambda:session)
    saves=[];monkeypatch.setattr(lk,'_media_save_session',lambda value:saves.append(value))
    monkeypatch.setattr(media_offline,'keep',lambda *a,**kw:target)
    answers=iter([str(tmp_path/'travel'),'y']);monkeypatch.setattr('builtins.input',lambda *_:next(answers))
    assert lk._media_keep_offline([row])=='1 available offline'
    saved=json.loads(lk.MEDIA_LIBRARY_FILE.read_text())['entries'][0]
    assert saved['artist']=='Artist' and saved['title']=='Song'
    assert saved['digest']=='sha256:'+row['digest']
    assert saves[-1]['queue'][0]['locations'][-1]['path']==str(target)
    assert saves[-1]['queue'][0]['locations'][-1]['node']=='laptop'


def test_active_oracle_worker_receives_cancellation(monkeypatch):
    fc=load_fc();entered=threading.Event();finished=threading.Event()
    def chat(prompt,history,mode,cancel_event):
        entered.set();cancel_event.wait(2);finished.set();raise InterruptedError('cancelled')
    monkeypatch.setattr(fc,'_shared_lo_chat',chat)
    oracle=fc.Oracle('http://unreachable','model');oracle.start();oracle.ask('ask','hello')
    assert entered.wait(1)
    oracle.cancel();assert finished.wait(1)
    oracle.stop.set();oracle.join(1)
    assert not oracle.is_alive() and oracle.responses.empty()


def test_cancelling_shared_oracle_terminates_owned_process(monkeypatch):
    import subprocess
    import sys
    fc=load_fc();cancel=threading.Event();processes=[]
    real_popen=subprocess.Popen
    def owned(*args,**kwargs):
        process=real_popen([sys.executable,'-c','import time;time.sleep(30)'],**kwargs)
        processes.append(process);cancel.set();return process
    monkeypatch.setattr(fc.subprocess,'Popen',owned)
    with pytest.raises(InterruptedError):fc._shared_lo_chat('hello',cancel_event=cancel)
    assert processes and processes[0].poll() is not None


def test_unmounted_travel_destination_is_not_created(lk,monkeypatch,tmp_path):
    monkeypatch.setattr(lk,'HOME',tmp_path)
    monkeypatch.setattr(lk,'_media_local_node_names',lambda:{'local'})
    missing=tmp_path/'unmounted-drive'
    monkeypatch.setattr('builtins.input',lambda *_:str(missing))
    message=lk._media_keep_offline([source(b'audio')])
    assert 'mount your travel drive first' in message and not missing.exists()
