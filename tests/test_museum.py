import io,json,time
from pathlib import Path
from unittest.mock import Mock
import pytest
from core import museum,museum_web,node,recovery
import museum_art,player_visuals,saver,museum_desk
from test_browser_fabric_views import load

JPEG=b'\xff\xd8\xfftest'

def art(ident='aic-1'):
    return dict(id=ident,title='A landscape',artist='Artist',date='1890',medium='Oil',culture='France',description='A view',museum='Museum',source='aic' if ident.startswith('aic') else 'met',rights='CC0',source_url='https://www.artic.edu/artworks/1',image_url='https://www.artic.edu/iiif/2/abc/full/1686,/0/default.jpg')


def test_only_open_access_images_and_identity():
    assert museum.record('met',{'isPublicDomain':False}) is None
    assert museum.record('aic',{'is_public_domain':True}) is None
    row=museum.record('met',{'objectID':1,'isPublicDomain':True,'primaryImage':'https://images.metmuseum.org/a.jpg','title':'<b>Art</b>\x1b[2J','objectURL':'javascript:evil'})
    assert row['rights']=='CC0' and '<b>' not in row['title'] and '\x1b' not in row['title']
    assert row['source_url']=='https://www.metmuseum.org/art/collection/search/1'
    for ident in ('../x','aic-0','met-1/abc','other-1'):
        with pytest.raises(ValueError):museum.identity(ident)
    for url in ('http://images.metmuseum.org/a','https://evil.org/a','https://images.metmuseum.org.evil/a','https://user@www.artic.edu/a','https://www.artic.edu:123/a'):
        with pytest.raises(ValueError):museum.allowed(url)


def test_collection_atomic_idempotent_and_offline(tmp_path,monkeypatch):
    m=museum.Museum(tmp_path);monkeypatch.setattr(museum,'detail',lambda _:art())
    fetch=Mock(return_value=JPEG);monkeypatch.setattr(museum,'fetch',fetch)
    row=m.save('aic-1');m.save('aic-1');assert fetch.call_count==1
    assert row['bytes']==len(JPEG) and m.image('aic-1').read_bytes()==JPEG
    assert m.snapshot('landscape')['items'][0]['downloaded']
    assert not m.snapshot('unrelated')['items']
    m.favorite('aic-1');assert museum.Museum(tmp_path).snapshot()['items'][0]['favorite']
    m.image('aic-1').unlink();assert not m.snapshot()['items'][0]['downloaded']
    with pytest.raises(ValueError):m.store(art(),b'<svg>not raster</svg>')
    monkeypatch.setattr(museum,'MAX_COLLECTION_BYTES',1)
    with pytest.raises(ValueError,match='budget'):m.store(art(),JPEG)


def test_starter_is_bounded_diverse_and_restart_reports_interruption(tmp_path,monkeypatch):
    m=museum.Museum(tmp_path);calls=[]
    def search(source,query,page):
        calls.append((source,query,page));return {'items':[art(source+'-'+str(len(calls)*100+i)) for i in range(1,21)]}
    monkeypatch.setattr(m,'search',search);monkeypatch.setattr(m,'save',lambda *a:None)
    m.start_pack(4);m.worker.join(2)
    state=m.snapshot()['job'];assert state['state']=='complete' and state['saved']==4
    assert len(calls)==4 and {x[0] for x in calls}=={'aic','met'}
    for count in (0,1001):
        with pytest.raises(ValueError):m.start_pack(count)
    state=m.read();state['job']['state']='running';m.write(state)
    assert museum.Museum(tmp_path).snapshot()['job']['state']=='interrupted'


def test_catalog_in_recovery_inventory_but_images_not_in_small_capsule(tmp_path):
    folder=tmp_path/'.local/share/future-crash-look';folder.mkdir(parents=True)
    (folder/'museum.json').write_text('{}');(folder/'museum/images').mkdir(parents=True);(folder/'museum/images/aic-1.jpg').write_bytes(JPEG)
    paths,_=recovery.sources(tmp_path)
    assert folder/'museum.json' in paths
    assert folder/'museum/images/aic-1.jpg' not in paths


@pytest.mark.parametrize('surface',['signal-window','albert'])
@pytest.mark.parametrize('path',['/museum','/api/museum','/api/museum/search','/api/museum/image'])
def test_web_requires_authorization(surface,path,monkeypatch):
    module=load(surface);h=module.Handler.__new__(module.Handler);h.path=path;h._require_endpoint=Mock(return_value=False)
    gateway=Mock();monkeypatch.setattr(museum_web,'handle',gateway)
    h.do_GET();h._require_endpoint.assert_called_once_with('lo.use');gateway.assert_not_called()


def test_web_mutation_rejects_cross_origin():
    h=Mock();h.headers={'Content-Type':'application/json','Origin':'https://other','Host':'host'}
    with pytest.raises(ValueError,match='Same-origin'):museum_web.post(h,'http://local')


def test_shared_visual_empty_and_bounded(tmp_path,monkeypatch):
    monkeypatch.setattr(Path,'home',lambda:tmp_path);museum_art._checked=0;museum_art._stamp=None
    assert 'Museum' in saver.SCENES
    mode=player_visuals.NAMES.index('Museum')+1
    for width,height in ((1,1),(20,5),(80,24)):
        rows=player_visuals.frame(mode,width,height,0)
        assert len(rows)==height and all(len(row)==width for row in rows)


def test_node_offline_pin_uses_peer_image_and_digest(tmp_path,monkeypatch):
    m=museum.Museum(tmp_path);row=art();row['sha256']=museum.hashlib.sha256(JPEG).hexdigest()
    h=object.__new__(node.API);h.path='/v1/museum?target=peer';h._file_target=lambda:({'name':'peer'},'/');h.sendj=lambda code,value:(code,value)
    monkeypatch.setattr(node,'_museum',lambda:m);monkeypatch.setattr(node,'identity',lambda:{'name':'local'})
    monkeypatch.setattr(node,'_file_peer_json',lambda *a:{'items':[row]});monkeypatch.setattr(node,'_copy_route',lambda p:'http://peer')
    monkeypatch.setattr(node.FABRIC_IDENTITY,'auth_headers_for_url',lambda _:{});monkeypatch.setattr(node.FABRIC_IDENTITY,'ssl_context_for_url',lambda _:None)
    monkeypatch.setattr(node.urllib.request,'urlopen',lambda *a,**k:io.BytesIO(JPEG))
    code,data=h._museum_request({'action':'pin','id':'aic-1'})
    assert code==200 and data['items'][0]['downloaded'] and m.image('aic-1').read_bytes()==JPEG
    row['sha256']='wrong';assert h._museum_request({'action':'pin','id':'aic-1'})[0]==400


def test_offline_cli_reads_local_catalog_without_service(tmp_path,monkeypatch):
    monkeypatch.setattr(Path,'home',lambda:tmp_path)
    m=museum.Museum();m.store(art(),JPEG)
    client=museum_desk.Client('local');monkeypatch.setattr(client,'request',Mock(side_effect=OSError('offline')))
    assert client.snapshot()['items'][0]['downloaded'] and client.snapshot()['offline']


def test_copy_collection_is_verified_and_reuses_local_files(tmp_path):
    m=museum.Museum(tmp_path);row=art();row.update(downloaded=True,sha256=museum.hashlib.sha256(JPEG).hexdigest())
    loader=Mock(return_value=JPEG)
    m.start_sync([row],loader);m.worker.join(2)
    assert m.snapshot()['job']['state']=='complete'
    m.start_sync([row],loader);m.worker.join(2)
    assert loader.call_count==1
    row=dict(row,id='aic-2',sha256='invalid')
    m.start_sync([row],loader);m.worker.join(2)
    assert m.snapshot()['job']['state']=='partial'
    with pytest.raises(ValueError):m.image('aic-2')


def test_remote_discovery_has_its_own_timeout_and_image_streaming(monkeypatch):
    from core import ingress
    assert ingress._is_stream_path('/v1/museum/image')
    assert ingress._request_timeout('/v1/museum/search','GET',None,False)==90
    assert ingress._request_timeout('/v1/museum','POST',b'{}',False)==90
    h=object.__new__(node.API);h.path='/v1/museum/search?target=peer&q=landscape&source=met'
    h._file_target=lambda:({'name':'peer'},'/');h.sendj=lambda code,value:(code,value)
    monkeypatch.setattr(node,'_copy_route',lambda p:'http://peer')
    call=Mock(return_value={'ok':True,'items':[]});monkeypatch.setattr(node,'http_json',call)
    assert h._museum_request()[0]==200
    assert call.call_args.kwargs['timeout']==90
    assert '/v1/museum/search?' in call.call_args.args[0]
