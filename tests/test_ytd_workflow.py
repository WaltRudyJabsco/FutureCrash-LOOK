"""Download lifecycle and catalog tests without fetching external media."""
import json
import os
import sys
import time
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'look'))
from core.downloads import Downloads, youtube_url
import file_catalog
import media_core
import media_watch
import weather_forecast
import ytd


def finished(manager,job):
    deadline=time.monotonic()+5
    while time.monotonic()<deadline:
        row=manager.get(job)
        if row['stage'] in {'complete','failed','cancelled'}: return row
        time.sleep(.01)
    raise AssertionError(manager.get(job))


def downloader(tmp_path,monkeypatch,index=None):
    script=tmp_path/'fake-yt-dlp'
    script.write_text('''#!'''+sys.executable+'''
import json,sys
from pathlib import Path
stage=Path(sys.argv[sys.argv.index('-P')+1]); stage.mkdir(exist_ok=True)
file=stage/'A title with spaces.mp4'; file.write_bytes(b'video')
(stage/'A title with spaces.info.json').write_text(json.dumps({'title':'A title with spaces','description':'An explanation of ukulele chord voicings','tags':['ukulele'],'channel':'Music lesson'}))
(stage/'fragment.part').write_bytes(b'fragment')
print('LOOK_PROGRESS:'+json.dumps({'downloaded_bytes':5,'total_bytes':5,'status':'finished'}),flush=True)
print('LOOK_FILE:'+json.dumps(str(file)),flush=True)
''')
    script.chmod(0o755)
    monkeypatch.setattr('core.downloads.binary',lambda name:str(script) if name=='yt-dlp' else '/usr/bin/true')
    return Downloads(tmp_path/'state',index=index)


def test_publish_only_completed_files_and_register_description(tmp_path,monkeypatch):
    db=tmp_path/'catalog.db'
    def index(row):
        file_catalog.register(db,row['file'],dict(summary=row['metadata']['description'],keywords=['ukulele'],source_url=row['url'],provenance='source'))
    manager=downloader(tmp_path,monkeypatch,index)
    row=finished(manager,manager.create('https://youtu.be/test',str(tmp_path/'Storage with spaces'))['id'])
    assert row['stage']=='complete' and row['indexed']
    assert row['expires_at'] is None
    assert set(p.suffix for p in Path(row['directory']).iterdir())=={'.mp4','.json'}
    hits=file_catalog.combined_search(db,'ukulele voicings')
    assert hits[0]['provenance']=='source' and hits[0]['path']==row['file']
    assert hits[0]['source_url']=='https://youtu.be/test'
    assert not list((tmp_path/'Storage with spaces').glob('.look-ytd-stage-*'))


def test_holding_expires_only_its_unchanged_manifest(tmp_path,monkeypatch):
    manager=downloader(tmp_path,monkeypatch)
    row=finished(manager,manager.create('https://youtu.be/test',str(tmp_path/'holding'),holding=True)['id'])
    unrelated=tmp_path/'holding'/'unrelated.mp4'; unrelated.write_bytes(b'keep')
    manager.expire(row['expires_at']+1)
    assert manager.get(row['id'])['stage']=='expired'
    assert unrelated.read_bytes()==b'keep'


def test_changed_or_extra_files_are_retained(tmp_path,monkeypatch):
    manager=downloader(tmp_path,monkeypatch)
    row=finished(manager,manager.create('https://youtu.be/test',str(tmp_path/'holding'),holding=True)['id'])
    extra=Path(row['directory'])/'my-note.txt'; extra.write_text('keep')
    manager.expire(row['expires_at']+1)
    assert manager.get(row['id'])['expires_at'] is None
    assert Path(row['file']).exists() and extra.exists()


def test_keep_moves_then_registers_permanent_item(tmp_path,monkeypatch):
    indexed=[]; manager=downloader(tmp_path,monkeypatch,indexed.append)
    row=finished(manager,manager.create('https://youtu.be/test',str(tmp_path/'holding'),holding=True)['id'])
    kept=manager.keep(row['id'],str(tmp_path/'permanent'))
    assert not kept['holding'] and kept['expires_at'] is None
    assert Path(kept['file']).exists() and not Path(row['file']).exists()
    assert indexed[-1]['file']==kept['file']
    manager.expire(time.time()+31*86400)
    assert Path(kept['file']).exists()


def test_index_failure_preserves_download_and_can_retry(tmp_path,monkeypatch):
    def broken(row): raise OSError('catalog locked')
    manager=downloader(tmp_path,monkeypatch,broken)
    row=finished(manager,manager.create('https://youtu.be/test',str(tmp_path/'downloads'))['id'])
    assert row['stage']=='complete' and not row['indexed'] and Path(row['file']).exists()
    manager.index=lambda row:None
    assert manager.reindex(row['id'])['indexed']


def test_invalid_sources_and_job_ids(tmp_path):
    import pytest
    for url in ('https://youtube.com.evil.test/video','file:///etc/passwd','https://user@youtube.com/watch?v=x'):
        with pytest.raises(ValueError): youtube_url(url)
    manager=Downloads(tmp_path/'state')
    with pytest.raises(ValueError): manager.get('../escape')


def test_refresh_existing_detects_new_file_and_preserves_metadata(tmp_path,monkeypatch):
    monkeypatch.setattr(Path,'home',classmethod(lambda cls:tmp_path))
    library=tmp_path/'library.json'; monkeypatch.setattr(media_watch,'LIBRARY',library)
    monkeypatch.setattr(media_watch,'STATUS',tmp_path/'status.json')
    root=tmp_path/'music'; root.mkdir(); first=root/'first.mp3'; first.write_bytes(b'one')
    lib=media_core.scan_root(root); lib['entries'][0]['title']='Curated title'; media_watch.save(lib)
    previous=media_watch.refresh_existing({})
    second=root/'second.mp4'; second.write_bytes(b'two')
    media_watch.refresh_existing(previous)
    rows=media_watch.load()['entries']
    assert len(rows)==2 and next(row for row in rows if row['path']==str(first))['title']=='Curated title'
    second.unlink(); media_watch.refresh_existing({})
    assert len(media_watch.load()['entries'])==1


def test_weather_dates_follow_forecast_location_not_host_clock():
    from datetime import date,timedelta
    today=date(2026,10,8)
    forecast=[{'date':(today+timedelta(days=n)).isoformat(),'high_f':70,'low_f':50,'precip_probability_pct':20,'weather_code':0} for n in range(8)]
    assert weather_forecast.selection('tomorrow',forecast)[0]['date']=='2026-10-09'
    assert len(weather_forecast.selection('five-day forecast',forecast))==5
    assert len(weather_forecast.selection('7-day forecast',forecast))==7
    assert [day['date'] for day in weather_forecast.selection('weekend',forecast)]==['2026-10-10','2026-10-11']
    output=weather_forecast.format_forecast({'requested':'tomorrow','forecast':forecast,'location':{'name':'Portland'},'timezone':'America/Los_Angeles'},lambda code:'Clear')
    assert '2026-10-09' in output and '2026-10-08' not in output and 'America/Los_Angeles' in output


def test_client_routes_to_node_and_preserves_literal_spaces():
    response=type('Response',(),{'__enter__':lambda self:self,'__exit__':lambda *args:None,'read':lambda self:b'{"ok":true,"job":{}}'})()
    with patch('urllib.request.urlopen',return_value=response) as call:
        ytd.request('download',node='3090',url='https://youtu.be/test',directory='/run/media/2TB Storage')
    req=call.call_args.args[0]
    assert 'target=3090' in req.full_url
    assert json.loads(req.data)['directory']=='/run/media/2TB Storage'


def test_remote_download_is_submitted_once_and_never_runs_locally(monkeypatch):
    from core import node
    handler=object.__new__(node.API)
    handler.path='/v1/downloads?target=3090'
    handler._file_target=lambda:({'name':'3090'},'/')
    receipts=[]; handler.sendj=lambda code,body:receipts.append((code,body))
    monkeypatch.setattr(node,'_downloads',lambda:(_ for _ in ()).throw(AssertionError('local download started')))
    monkeypatch.setattr(node,'_copy_route',lambda peer:'https://3090')
    calls=[]
    def send(url,data=None,**kwargs):
        calls.append((url,data)); raise TimeoutError('No confirmation')
    monkeypatch.setattr(node,'http_json',send)
    handler._downloads_request({'action':'download','url':'https://youtu.be/test'})
    assert len(calls)==1 and calls[0][0]=='https://3090/v1/downloads'
    assert receipts[0][0]==400 and not receipts[0][1]['ok']


def test_remote_status_uses_read_only_cached_route(monkeypatch):
    from core import node
    handler=object.__new__(node.API); handler.path='/v1/downloads/'+'a'*32+'?target=3090'
    handler._file_target=lambda:({'name':'3090'},'/')
    calls=[]; handler.sendj=lambda code,body:(code,body)
    monkeypatch.setattr(node,'_file_peer_json',lambda peer,path:calls.append(path) or {'ok':True,'node':'3090','job':{'stage':'downloading'}})
    code,result=handler._downloads_request()
    assert code==200 and result['node']=='3090'
    assert calls==['/v1/downloads/'+'a'*32]


def test_node_catalog_search_includes_source_descriptions(tmp_path,monkeypatch):
    from core import node
    path=tmp_path/'lesson.mp4'; path.write_bytes(b'video'); db=tmp_path/'files.db'
    file_catalog.register(db,path,dict(summary='Ukulele chord voicings and fretboard navigation',keywords=['ukulele'],provenance='source'))
    monkeypatch.setattr(node,'LOOK_FILE_CATALOG',db)
    monkeypatch.setattr(node,'identity',lambda:{'name':'3090'})
    result=node._local_file_search('ukulele voicings')
    assert result['count']==1 and result['entries'][0]['provenance']=='source'
    assert result['entries'][0]['node']=='3090'


def test_next_week_uses_next_monday():
    from datetime import date,timedelta
    forecast=[{'date':(date(2026,10,8)+timedelta(days=n)).isoformat()} for n in range(16)]
    selected=weather_forecast.selection('next week',forecast)
    assert len(selected)==7 and selected[0]['date']=='2026-10-12' and selected[-1]['date']=='2026-10-18'


def test_restart_does_not_claim_an_unfinished_job_is_complete(tmp_path):
    manager=Downloads(tmp_path/'state'); manager.update('a'*32,stage='processing')
    restarted=Downloads(tmp_path/'state')
    assert restarted.get('a'*32)['stage']=='failed'
    assert 'restarted' in restarted.get('a'*32)['error']


def test_cancel_during_progress_does_not_revive_job(tmp_path,monkeypatch):
    import io, threading
    manager=Downloads(tmp_path/'state'); job='b'*32
    root=tmp_path/'downloads'; root.mkdir()
    manager.update(job,stage='queued',url='https://youtu.be/test',root=str(root),holding=False)
    ready=threading.Event(); resume=threading.Event()
    class Output:
        def __iter__(self):
            ready.set(); resume.wait(3)
            yield 'LOOK_PROGRESS:'+json.dumps({'status':'downloading','downloaded_bytes':1})
        def close(self): pass
    class Process:
        stdout=Output()
        def terminate(self): pass
        def wait(self): return 1
        def poll(self): return 1
    monkeypatch.setattr('core.downloads.binary',lambda name:'/usr/bin/true')
    monkeypatch.setattr('core.downloads.subprocess.Popen',lambda *args,**kwargs:Process())
    thread=threading.Thread(target=manager.run,args=(job,)); thread.start()
    assert ready.wait(3)
    manager.cancel(job); resume.set(); thread.join(3)
    assert not thread.is_alive() and manager.get(job)['stage']=='cancelled'
    assert not list(root.iterdir())
