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
