import io
import threading
from unittest.mock import Mock

import pytest
from core import node, file_transfer
from look import fabric_files as ff
from test_fabric_file_destinations import archive
import tarfile


def test_route_discovery_does_not_wait_for_a_stale_first_route(monkeypatch):
    release=threading.Event(); stale_done=threading.Event()
    def get(url,**kwargs):
        if url.startswith('http://stale'):
            release.wait(2); stale_done.set(); raise OSError('stale')
        return {'ok':True}
    monkeypatch.setattr(node,'http_json',get)
    try:
        assert node._copy_route({'url':'http://stale','tailcat_endpoints':['http://live']})=='http://live'
        assert not stale_done.is_set()
    finally: release.set()


def test_directory_navigation_reuses_live_route_and_falls_back_if_it_changes(monkeypatch):
    monkeypatch.setattr(node,'_FILE_ROUTES',{})
    calls=[]; fail=False
    def get(url,**kwargs):
        calls.append(url)
        if url.startswith('http://stale'): raise OSError('offline')
        if fail and url.startswith('http://live'): raise OSError('route changed')
        return {'ok':True,'path':url}
    monkeypatch.setattr(node,'http_json',get)
    peer={'url':'http://stale','tailcat_endpoints':['http://live']}
    assert 'live' in node._file_peer_json(peer,'/first')['path']
    calls.clear()
    assert node._file_peer_json(peer,'/second')['path']=='http://live/second'
    assert calls==['http://live/second']
    fail=True
    peer['tailcat_endpoints'].append('http://new')
    assert node._file_peer_json(peer,'/third')['path']=='http://new/third'


def test_incomplete_declared_body_cannot_publish_even_when_tar_members_are_complete(tmp_path):
    data=archive([('song.mp3',b'music',tarfile.REGTYPE)])
    reader=file_transfer.SizedReader(data,len(data.getvalue())+1024)
    with pytest.raises(ValueError,match='interrupted'):
        file_transfer.receive(reader,str(tmp_path),before_publish=reader.finish)
    assert list(tmp_path.iterdir())==[]


def test_upload_chunks_are_bounded_and_report_monotonic_progress():
    data=b'a'*(512*1024+3); records=[]
    reader=file_transfer.SizedReader(io.BytesIO(data),len(data),lambda count,total:records.append((count,total)),upload=True)
    chunks=[]
    while chunk:=reader.read(8192): chunks.append(chunk)
    assert b''.join(chunks)==data
    assert len(chunks)==3 and max(map(len,chunks))<=256*1024
    assert [count for count,_ in records]==sorted(count for count,_ in records)
    assert records[-1]==(len(data),len(data))


def test_preparation_and_confirmation_are_distinct_from_upload_completion(tmp_path,monkeypatch):
    path=tmp_path/'song.mp3'; path.write_bytes(b'music')
    updates=[]; progress=Mock(update=lambda **fields:updates.append(fields))
    monkeypatch.setattr(ff,'request',lambda *args,**kwargs:{'ok':True,'copied':['song.mp3']})
    result=ff.copy([path],'@3090:~/Downloads',progress)
    stages=[row['stage'] for row in updates]
    assert stages[0]=='preparing' and 'connecting' in stages and stages[-1]=='complete'
    assert result['elapsed']>=0
    text=ff.progress_text({'stage':'confirming','bytes':1024,'total':1024},3)
    assert '100.0%' in text and 'awaiting confirmation' in text and 'copy confirmed' not in text


def test_completed_progress_records_are_evicted_without_blocking_new_copies(monkeypatch):
    monkeypatch.setattr(node,'_COPY_TRANSFERS',{})
    for index in range(70): node._copy_progress(f'{index:032x}',stage='complete')
    assert len(node._COPY_TRANSFERS)==64
