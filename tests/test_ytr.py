import json
from pathlib import Path
from unittest.mock import Mock
import pytest
from core.radio import Radio, canonical_url
from core.downloads import audio_options
import ytr
import player_visuals
import saver


class Downloads:
    def __init__(self):self.jobs={}
    def create(self,url,**kwargs):
        assert kwargs['audio'] is True
        job={'id':str(len(self.jobs)),'stage':'queued','audio':True}
        self.jobs[job['id']]=job;return job
    def get(self,key):return self.jobs[key]
    def cancel(self,key):self.jobs[key]['stage']='cancelled'


@pytest.mark.parametrize('url',['https://youtu.be/abcdefghijk?t=30','https://www.youtube.com/watch?v=abcdefghijk&list=foo','https://youtube.com/shorts/abcdefghijk'])
def test_identity_dedup(url):assert canonical_url(url)=='https://www.youtube.com/watch?v=abcdefghijk'

@pytest.mark.parametrize('url',['https://youtube.com/playlist?list=foo','https://evil.example/watch?v=abcdefghijk','https://youtube.com/watch?v=bad','file:///tmp/a'])
def test_reject_non_video_links(url):
    with pytest.raises(ValueError):canonical_url(url)


def test_queue_bookmarks_conflicts_and_order(tmp_path):
    downloads=Downloads();radio=Radio(downloads,tmp_path)
    a=radio.change({'action':'add','url':'https://youtu.be/abcdefghijk'})['items'][0]
    radio.change({'action':'add','url':'https://youtube.com/watch?v=abcdefghijk&t=20'})
    assert len(downloads.jobs)==1
    b=radio.change({'action':'add','url':'https://youtu.be/12345678901'})['items'][1]
    radio.change({'action':'move','id':b['id'],'delta':-1})
    assert radio.snapshot()['items'][0]['id']==b['id']
    update=dict(action='progress',id=a['id'],position=42,bookmark_revision=0)
    radio.change(update)
    with pytest.raises(ValueError,match='another device'):radio.change(update)
    assert Radio(downloads,tmp_path).snapshot()['items'][1]['position']==42
    radio.change({'action':'remove','id':b['id']})
    assert len(radio.snapshot()['items'])==1


def test_audio_selector_never_requests_video():
    assert audio_options()==['-f','bestaudio','-x','--audio-format','m4a']


def test_audio_export_is_confined_to_owned_completed_job(tmp_path):
    downloads=Downloads();radio=Radio(downloads,tmp_path)
    item=radio.change({'action':'add','url':'https://youtu.be/abcdefghijk'})['items'][0]
    with pytest.raises(ValueError):radio.audio_file(item['id'])
    outside=tmp_path/'outside.m4a';outside.write_bytes(b'audio')
    downloads.jobs[item['job']].update(stage='complete',file=str(outside))
    with pytest.raises(ValueError,match='unavailable'):radio.audio_file(item['id'])
    owned=tmp_path/'audio'/'test.m4a';owned.parent.mkdir();owned.write_bytes(b'audio')
    downloads.jobs[item['job']]['file']=str(owned)
    assert radio.audio_file(item['id'])==owned


def test_offline_resume_and_repeated_online_bookmarks(tmp_path,monkeypatch):
    client=ytr.Client('owner',tmp_path);item={'id':'a'*32,'bookmark_revision':0,'position':0,'done':False,'stage':'complete'}
    state={'ok':True,'node':'owner','items':[item]}
    def request(action=None,**fields):
        if action:
            assert fields['bookmark_revision']==item['bookmark_revision']
            item.update(position=fields['position'],bookmark_revision=item['bookmark_revision']+1)
        return state
    monkeypatch.setattr(client,'request',request)
    client.snapshot();stale=dict(item)
    client.checkpoint(stale,12);client.sync();client.checkpoint(stale,24);client.sync()
    assert item['position']==24
    client.checkpoint(stale,30)
    monkeypatch.setattr(client,'request',Mock(side_effect=OSError('offline')))
    assert client.snapshot()['items'][0]['position']==30 and client.offline
    with pytest.raises(OSError):client.sync()
    assert client.pending()[item['id']]['position']==30


@pytest.mark.parametrize('name',['Tape Echo','Deep Space Relay'])
@pytest.mark.parametrize('size',[(1,1),(40,10),(120,40)])
def test_new_animations_are_bounded_deterministic_and_available_to_saver(name,size):
    mode=player_visuals.NAMES.index(name)+1;width,height=size
    a=player_visuals.frame(mode,width,height,2,seed=5)
    assert len(a)==height and all(len(row)==width for row in a)
    assert a==player_visuals.frame(mode,width,height,2,seed=5)
    assert name in saver.SCENES
    assert player_visuals.frame(mode,width,height,2,False)==player_visuals.frame(mode,width,height,9,False)


def test_client_cache_is_atomic_and_usable_without_owner(tmp_path,monkeypatch):
    import io
    class Response(io.BytesIO):
        headers={'Content-Length':'5'}
    client=ytr.Client('owner',tmp_path);item={'id':'b'*32,'stage':'complete'}
    monkeypatch.setattr(ytr.urllib.request,'urlopen',lambda *a,**k:Response(b'audio'))
    path=client.prepare(item);assert path.read_bytes()==b'audio'
    monkeypatch.setattr(ytr.urllib.request,'urlopen',Mock(side_effect=OSError('offline')))
    assert client.prepare(item)==path
    path.unlink()
    with pytest.raises(OSError):client.prepare(item)
    assert not path.exists() and not path.with_suffix('.part').exists()


def test_node_radio_routes_owner_and_audio_without_shell(tmp_path,monkeypatch):
    from core import node
    radio=Radio(Downloads(),tmp_path)
    monkeypatch.setattr(node,'_radio',lambda:radio)
    monkeypatch.setattr(node,'identity',lambda:{'name':'owner'})
    handler=object.__new__(node.API);handler.path='/v1/radio'
    handler._file_target=lambda:(None,'/')
    handler.sendj=lambda code,payload:(code,payload)
    code,payload=handler._radio_request({'action':'add','url':'https://youtu.be/abcdefghijk'})
    assert code==200 and payload['ok'] and payload['node']=='owner'
    handler._file_target=lambda:({'name':'remote'},'/')
    monkeypatch.setattr(node,'_file_peer_json',lambda peer,path:{'ok':True,'node':peer['name'],'route':path})
    assert handler._radio_request()[1]['route']=='/v1/radio'


def test_download_job_uses_audio_only_format(tmp_path,monkeypatch):
    import sys,time
    from core.downloads import Downloads as Manager
    script=tmp_path/'downloader'
    script.write_text('#!'+sys.executable+'''\nimport sys,json
from pathlib import Path
assert sys.argv[sys.argv.index('-f')+1]=='bestaudio'
assert '--merge-output-format' not in sys.argv
stage=Path(sys.argv[sys.argv.index('-P')+1]);audio=stage/'episode.m4a';audio.write_bytes(b'audio')
(stage/'episode.info.json').write_text(json.dumps({'title':'Episode'}))
print('LOOK_FILE:'+json.dumps(str(audio)))
''');script.chmod(0o700)
    monkeypatch.setattr('core.downloads.binary',lambda _:str(script))
    manager=Manager(tmp_path/'jobs')
    job=manager.create('https://youtu.be/abcdefghijk',directory=str(tmp_path/'audio'),audio=True)
    deadline=time.monotonic()+5
    while time.monotonic()<deadline:
        row=manager.get(job['id'])
        if row['stage'] in {'complete','failed'}:break
        time.sleep(.01)
    assert row['stage']=='complete',row
    assert Path(row['file']).suffix=='.m4a' and row['metadata']['title']=='Episode'


def test_footer_is_painted_before_clear_without_trailing_scroll():
    frame=ytr.terminal_frame(['YOUTUBE RADIO','Queue'],['Enter play','Q quit'])
    assert frame=='\033[HYOUTUBE RADIO\033[K\nQueue\033[K\nEnter play\033[K\nQ quit\033[K\033[J'
    assert frame.count('\033[J')==1
    assert frame.index('Q quit')<frame.index('\033[J')
