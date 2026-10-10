import json
import os
from pathlib import Path
import shutil
import threading
import time
import uuid
from unittest.mock import Mock

import pytest
from look import disc_import as discs
from look import disc_ui
from look import media_core


@pytest.fixture
def isolated(tmp_path,monkeypatch):
    monkeypatch.setenv('HOME',str(tmp_path))
    monkeypatch.setattr(discs,'ROOT',tmp_path/'jobs-root')
    monkeypatch.setattr(discs,'LIBRARY',tmp_path/'media_library.json')
    monkeypatch.setattr(discs,'MIN_FREE_BYTES',1)
    return tmp_path


def seed(tmp_path,kind='cd',cancelled=False):
    identifier=uuid.uuid4().hex;destination=tmp_path/'media';destination.mkdir(exist_ok=True)
    row={'id':identifier,'kind':kind,'state':'queued','stage':'queued','created':time.time(),
         'drive':{'id':'test-drive','device':'/dev/fixture','mount':'','makemkv_source':'disc:0'},
         'destination':str(destination),'title':'A record','title_index':'0','metadata':{'artist':'Band','tracks':['First','Second']},
         'cancel_requested':cancelled,'percent':None}
    discs.atomic(discs.job_path(identifier),row);return identifier


def fake_tool(path,body):
    path.write_text('#!'+os.sys.executable+'\n'+body);path.chmod(0o755);return str(path)


def test_robot_progress_and_toc_are_stable():
    text=' 1. 100 [00:01.25] 0 [00:00.00]\n 2. 200 [00:02.50] 100 [00:01.25]'
    toc=discs.toc_from_query(text)
    assert toc['toc']=='1 2 450 150 250'
    assert len(toc['disc_id'])==28
    assert discs.progress('PRGV:20,40,100')==40
    assert discs.progress('Encoding: 37.25 %')==37.25
    assert discs.progress('reading') is None
    assert list(discs.robot_records('DRV:0,1,1,0,"USB drive","Disc, title","/dev/sr0"','DRV'))[0][5]=='Disc, title'


def test_drive_selection_and_job_ids_do_not_accept_arbitrary_paths(monkeypatch):
    monkeypatch.setattr(discs,'drives',lambda:{'drives':[{'id':'one','device':'/dev/sr0'},{'id':'two','device':'/dev/sr1'}]})
    with pytest.raises(ValueError,match='select'):discs.selected_drive(None)
    assert discs.selected_drive('/dev/sr1')['id']=='two'
    with pytest.raises(ValueError):discs.job_path('../../outside')


def test_mac_discovery_handles_plain_indices_and_each_drive_separately(monkeypatch):
    import plistlib
    monkeypatch.setattr(discs.sys,'platform','darwin')
    monkeypatch.setattr(discs,'tool',lambda name:name if name in {'drutil','diskutil'} else None)
    def query(command,timeout=30):
        if command==['drutil','list']:return '1 Vendor DVD 1.0\n2. Vendor Blu-ray 2.0\n'
        return 'Name: /dev/disk'+command[2]
    monkeypatch.setattr(discs,'query',query)
    monkeypatch.setattr(discs.subprocess,'run',lambda command,**kwargs:Mock(stdout=plistlib.dumps({'MountPoint':'/Volumes/'+command[-1].split('/')[-1]})))
    rows=discs.drives()['drives']
    assert [(row['id'],row['device'],row['mount']) for row in rows]==[
        ('drive:1','/dev/disk1','/Volumes/disk1'),('drive:2','/dev/disk2','/Volumes/disk2')]


def test_start_rejects_missing_title_and_busy_drive(isolated,monkeypatch):
    drive={'id':'test-drive','device':'/dev/fixture','mount':'','makemkv_source':'disc:0'}
    monkeypatch.setattr(discs,'selected_drive',lambda identifier:drive)
    monkeypatch.setattr(discs,'tool',lambda name:name)
    with pytest.raises(ValueError,match='title-index'):discs.start({'kind':'dvd','destination':str(isolated/'media')})
    identifier=seed(isolated);row=json.loads(discs.job_path(identifier).read_text());row['pid']=os.getpid();discs.atomic(discs.job_path(identifier),row)
    with pytest.raises(ValueError,match='already'):discs.start({'kind':'cd','destination':str(isolated/'media')})


def test_failed_spawn_leaves_a_terminal_receipt(isolated,monkeypatch):
    monkeypatch.setattr(discs,'selected_drive',lambda identifier:{'id':'test','device':'fixture'})
    monkeypatch.setattr(discs,'tool',lambda name:name)
    monkeypatch.setattr(discs.subprocess,'Popen',Mock(side_effect=OSError('spawn denied')))
    with pytest.raises(OSError):discs.start({'kind':'cd','destination':str(isolated/'media')})
    assert discs.list_jobs()[0]['state']=='failed'


@pytest.mark.skipif(not shutil.which('ffmpeg') or not shutil.which('ffprobe'),reason='Real media codecs unavailable')
def test_cd_worker_encodes_verifies_and_publishes_tagged_flac(isolated,monkeypatch):
    reader=fake_tool(isolated/'reader','''import wave,struct
for n in (1,2):
 with wave.open('track%02d.cdda.wav'%n,'wb') as out:
  out.setnchannels(1);out.setsampwidth(2);out.setframerate(8000);out.writeframes(struct.pack('<h',100)*8000)
''')
    original=discs.tool;monkeypatch.setattr(discs,'tool',lambda name:reader if name in {'cd-paranoia','cdparanoia'} else original(name))
    identifier=seed(isolated);discs.worker(identifier);job=discs.read_job(identifier)
    assert job['state']=='complete',job
    output=Path(job['output']);assert len(list(output.glob('*.flac')))==2
    assert not list(output.glob('*.wav'))
    rows=json.loads(discs.LIBRARY.read_text())['entries']
    assert [(row['artist'],row['album'],row['title'],row['track']) for row in rows]==[
        ('Band','A record','First',1),('Band','A record','Second',2)]
    assert job['percent']==100
    assert output.name.startswith('A record - ')


def test_failed_reader_preserves_partial_files_and_does_not_index(isolated,monkeypatch):
    reader=fake_tool(isolated/'reader',"from pathlib import Path\nPath('partial.wav').write_bytes(b'partial')\nraise SystemExit(2)\n")
    monkeypatch.setattr(discs,'tool',lambda name:reader)
    identifier=seed(isolated);discs.worker(identifier);job=discs.read_job(identifier)
    assert job['state']=='failed'
    assert (Path(job['partial_path'])/'partial.wav').read_bytes()==b'partial'
    assert not discs.LIBRARY.exists()


def test_cancellation_stops_tool_and_preserves_staging(isolated,monkeypatch):
    reader=fake_tool(isolated/'reader',"import time\nprint('reading',flush=True)\ntime.sleep(60)\n")
    monkeypatch.setattr(discs,'tool',lambda name:reader)
    identifier=seed(isolated);thread=threading.Thread(target=discs.worker,args=(identifier,));thread.start()
    deadline=time.monotonic()+5
    while discs.read_job(identifier)['state']!='running' and time.monotonic()<deadline:time.sleep(.01)
    discs.cancel(identifier);thread.join(timeout=6)
    assert not thread.is_alive()
    job=discs.read_job(identifier);assert job['state']=='cancelled'
    assert Path(job['partial_path']).is_dir() and not discs.LIBRARY.exists()


def test_video_worker_validates_stream_before_publication(isolated,monkeypatch):
    executable=fake_tool(isolated/'movie',"from pathlib import Path\nPath('title.mkv').write_bytes(b'invalid media')\n")
    monkeypatch.setattr(discs,'tool',lambda name:executable)
    monkeypatch.setattr(discs,'query',lambda *args:json.dumps({'streams':[],'format':{}}))
    identifier=seed(isolated,'bluray');discs.worker(identifier)
    assert discs.read_job(identifier)['state']=='failed' and not discs.LIBRARY.exists()


def test_ambiguous_metadata_is_not_chosen_silently():
    scan={'releases':[{'title':'Edition A'},{'title':'Edition B'}]}
    request=Mock(side_effect=[scan,{'ok':True}])
    disc_ui.capture(request,'drive','cd')
    assert 'metadata' not in request.call_args.args[1]
    request=Mock(side_effect=[scan,{'ok':True}]);disc_ui.capture(request,'drive','cd',release=2)
    assert request.call_args.args[1]['metadata']['title']=='Edition B'


def test_native_audio_tracks_use_numeric_order_and_supported_extensions(tmp_path):
    for name in ['10 Ten.aiff','2 Two.aif','1 One.AIFF','3 Three.aifc','cover.jpg']:
        (tmp_path/name).touch()
    assert [p.name for p in discs.audio_tracks(tmp_path)]==['1 One.AIFF','2 Two.aif','3 Three.aifc','10 Ten.aiff']


def test_native_audio_volume_permission_failure_is_actionable(monkeypatch,tmp_path):
    def denied(path):raise PermissionError('Operation not permitted')
    monkeypatch.setattr(Path,'iterdir',denied)
    with pytest.raises(ValueError,match='removable-volume access'):discs.audio_tracks(tmp_path)


def test_mac_toc_uses_absolute_offsets_without_second_leadin(tmp_path):
    import plistlib
    toc={'Sessions':[{'First Track':1,'Last Track':2,'Leadout Block':450,'Track Array':[
        {'Point':1,'Start Block':150,'Data':False},{'Point':2,'Start Block':250,'Data':False}]}]}
    (tmp_path/'.TOC.plist').write_bytes(plistlib.dumps(toc))
    native=discs.toc_from_mount(tmp_path)
    reader=discs.toc_from_query(' 1. 100 [00:01.25] 0 [00:00.00]\n 2. 200 [00:02.50] 100 [00:01.25]')
    assert native==reader
    toc['Sessions'][0]['Track Array'][1]['Data']=True
    (tmp_path/'.TOC.plist').write_bytes(plistlib.dumps(toc))
    assert discs.toc_from_mount(tmp_path) is None


def test_mac_scan_looks_up_toc_and_keeps_detected_labels(monkeypatch,tmp_path):
    import plistlib
    (tmp_path/'1 First.aiff').touch();(tmp_path/'2 Second.aiff').touch()
    (tmp_path/'.TOC.plist').write_bytes(plistlib.dumps({'Sessions':[{'First Track':1,'Last Track':2,'Leadout Block':450,'Track Array':[
        {'Point':1,'Start Block':150,'Data':False},{'Point':2,'Start Block':250,'Data':False}]}]}))
    monkeypatch.setattr(discs,'tool',lambda name:None)
    monkeypatch.setattr(discs,'selected_drive',lambda identifier:{'mount':str(tmp_path),'disc':'Album'})
    lookup=Mock(return_value=[{'title':'Album','artist':'Artist','tracks':['First','Second']}])
    monkeypatch.setattr(discs,'lookup',lookup)
    scan=discs.inspect(None)
    assert scan['engine']=='macOS audio volume'
    assert scan['metadata']=={'title':'Album','tracks':['First','Second']}
    assert lookup.call_args.args[0]['toc']=='1 2 450 150 250'
    assert scan['releases'][0]['artist']=='Artist'


def test_cd_capture_keeps_native_labels_without_release_match():
    request=Mock(side_effect=[{'metadata':{'title':'Album','tracks':['First']},'releases':[]},{'ok':True}])
    disc_ui.capture(request,'drive:1','cd')
    assert request.call_args.args[1]['metadata']=={'title':'Album','tracks':['First']}


def test_cover_download_is_bounded_and_preserves_existing_art(tmp_path,monkeypatch):
    import io
    response=Mock(side_effect=lambda *a,**k:io.BytesIO(b'\xff\xd8\xfffixture'))
    monkeypatch.setattr(discs.urllib.request,'urlopen',response)
    release='9a5496e4-f879-4805-af51-d3ecdab83911'
    result=discs.download_cover(tmp_path,release)
    assert result['state']=='downloaded'
    assert (tmp_path/'cover.jpg').read_bytes()==b'\xff\xd8\xfffixture'
    assert discs.download_cover(tmp_path,release)['state']=='existing'
    assert response.call_count==1
    assert not list(tmp_path.glob('.cover-*'))


@pytest.mark.parametrize('data',[b'<html>error</html>',b'\xff\xd8\xff'+b'x'*discs.COVER_MAX_BYTES])
def test_bad_cover_does_not_publish(tmp_path,monkeypatch,data):
    import io
    monkeypatch.setattr(discs.urllib.request,'urlopen',lambda *a,**k:io.BytesIO(data))
    assert discs.download_cover(tmp_path,'9a5496e4-f879-4805-af51-d3ecdab83911')['state']=='unavailable'
    assert not (tmp_path/'cover.jpg').exists()


def test_cover_outage_and_unknown_release_are_optional(tmp_path,monkeypatch):
    response=Mock(side_effect=OSError('offline'))
    monkeypatch.setattr(discs.urllib.request,'urlopen',response)
    assert discs.download_cover(tmp_path,None)['state']=='unavailable'
    response.assert_not_called()
    assert discs.download_cover(tmp_path,'9a5496e4-f879-4805-af51-d3ecdab83911')['state']=='unavailable'
    assert not list(tmp_path.iterdir())
