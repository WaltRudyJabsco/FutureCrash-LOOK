import json
from pathlib import Path
from unittest.mock import Mock
import pytest
from look import media_storage as storage
from look import fabric_files


@pytest.fixture
def home(monkeypatch,tmp_path):
    monkeypatch.setenv('HOME',str(tmp_path));return tmp_path


def data(root,source,identifier='a'*32):
    return {'destination':str(root),'folder':source.name,'category':'music','id':identifier,'manifest':storage.manifest(source)}


def test_defaults_are_per_node_with_override_and_all_categories(home):
    assert storage.destination('cd')=='~/Media/music'
    storage.settings({'node':'3090','root':'/media/library'})
    assert storage.destination('cd')=='@3090:/media/library'
    assert storage.settings()['node']=='3090'
    owner=storage.owner_request('settings',{'root':'~/Media'})
    assert all((home/'Media'/name).is_dir() for name in ('music','movies','tv','books','inbox'))
    assert storage.settings()['node']=='3090'
    assert json.loads((home/'.config/look/media_library.json').read_text())['root']=='~/Media'


def test_prepare_then_verified_inbox_publish_indexes_and_preserves_source(home):
    root=home/'library';source=home/'Album';source.mkdir();(source/'01 First.flac').write_bytes(b'audio')
    (source/'01 First.info.json').write_text('{"artist":"Artist","album":"Album"}')
    payload=data(root,source);prepared=storage.owner_request('prepare',payload)
    import shutil
    shutil.copytree(source,Path(prepared['path'])/prepared['stage'])
    assert not (root/'music'/source.name).exists()
    result=storage.owner_request('publish',payload)
    assert result['verified_files']==2 and source.is_dir()
    assert (root/'music'/source.name/'01 First.flac').read_bytes()==b'audio'
    library=json.loads((home/'.local/share/look/media_library.json').read_text())
    assert library['entries'][0]['artist']=='Artist'
    assert storage.owner_request('publish',payload)['cataloged']


def test_corrupt_inbox_does_not_publish_or_catalog(home):
    root=home/'library';source=home/'Album';source.mkdir();(source/'song.flac').write_bytes(b'audio')
    payload=data(root,source);prepared=storage.owner_request('prepare',payload)
    stage=Path(prepared['path'])/prepared['stage'];stage.mkdir();(stage/'song.flac').write_bytes(b'wrong')
    with pytest.raises(ValueError,match='checksums differ'):storage.owner_request('publish',payload)
    assert stage.exists() and not (root/'music'/source.name).exists()
    assert not (home/'.local/share/look/media_library.json').exists()


def test_existing_different_library_album_is_never_overwritten(home):
    root=home/'library';source=home/'Album';source.mkdir();(source/'song.flac').write_bytes(b'audio')
    payload=data(root,source);storage.owner_request('prepare',payload)
    target=root/'music'/'Album';target.mkdir();(target/'song.flac').write_bytes(b'original')
    with pytest.raises(ValueError):storage.owner_request('publish',payload)
    assert (target/'song.flac').read_bytes()==b'original'


def test_failed_delivery_retains_source_and_durable_error(home,monkeypatch):
    path=storage.receipt_path('a'*32);path.parent.mkdir(parents=True)
    source=home/'Album';source.mkdir();(source/'song.flac').write_bytes(b'audio')
    storage.atomic(path,{'id':'a'*32,'source':str(source),'destination':'@3090:~/Media','category':'music','state':'queued'})
    monkeypatch.setattr(storage,'remote',Mock(side_effect=RuntimeError('Node asleep')))
    storage.worker('a'*32)
    assert json.loads(path.read_text())['state']=='failed' and source.is_dir()


def test_named_archive_root_is_literal_and_verifies_entire_delivery(home,monkeypatch):
    source=home/'Album';source.mkdir();(source/'song.flac').write_bytes(b'audio')
    import tarfile
    def receive(route,params,stream,length):
        with tarfile.open(fileobj=stream,mode='r:') as archive:
            assert archive.getnames()==['.look-delivery-test','.look-delivery-test/song.flac']
        return {'ok':True}
    monkeypatch.setattr(fabric_files,'request',receive)
    fabric_files.copy([source],'@3090:~/Media/inbox',root_name='.look-delivery-test')
    with pytest.raises(ValueError):fabric_files.copy([source],'@3090:~/Media/inbox',root_name='../escape')


def test_delivery_worker_copies_through_inbox_then_verifies_and_catalogs(home,monkeypatch):
    import shutil
    root=home/'recipient';source=home/'Album';source.mkdir();(source/'song.flac').write_bytes(b'audio')
    identifier='b'*32;path=storage.receipt_path(identifier);path.parent.mkdir(parents=True)
    storage.atomic(path,{'id':identifier,'source':str(source),'destination':'@3090:'+str(root),'category':'music','state':'queued'})
    def remote(action,dest,payload):return storage.owner_request(action,dict(payload,destination=dest.path))
    def copy(paths,destination,progress=None,root_name=None):
        dest=fabric_files.parse(destination)
        assert dest.path==str(root/'inbox') and root_name=='.look-delivery-'+identifier
        shutil.copytree(paths[0],Path(dest.path)/root_name);return {'ok':True}
    monkeypatch.setattr(storage,'remote',remote);monkeypatch.setattr(fabric_files,'copy',copy)
    storage.worker(identifier)
    row=json.loads(path.read_text())
    assert row['state']=='complete' and row['verified_files']==1 and source.exists()
    assert row['output']==str(root/'music'/'Album')


def test_spawn_failure_is_recorded_without_losing_source(home,monkeypatch):
    monkeypatch.setattr(storage.subprocess,'Popen',Mock(side_effect=OSError('spawn denied')))
    with pytest.raises(OSError):storage.start('a'*32,home/'Album','@3090:~/Media')
    assert storage.receipt('a'*32)['state']=='failed'


def test_cancellation_never_signals_a_reused_worker_pid(home,monkeypatch):
    path=storage.receipt_path('a'*32);path.parent.mkdir(parents=True)
    storage.atomic(path,{'id':'a'*32,'state':'running','pid':123})
    monkeypatch.setattr(storage.os,'kill',lambda *args:None)
    monkeypatch.setattr(storage.subprocess,'run',lambda *args,**kwargs:Mock(stdout='unrelated process'))
    killed=Mock();monkeypatch.setattr(storage.os,'killpg',killed)
    with pytest.raises(ValueError,match='identity changed'):storage.cancel('a'*32)
    killed.assert_not_called()
