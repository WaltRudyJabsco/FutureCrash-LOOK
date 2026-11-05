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


def test_collection_navigation_wraps_and_skips_online():
    rows=[dict(id='aic-1',downloaded=True),dict(id='aic-2',downloaded=False),dict(id='aic-3',downloaded=True)]
    assert museum_desk.adjacent_artwork(rows,0,1)==2
    assert museum_desk.adjacent_artwork(rows,2,1)==0
    assert museum_desk.adjacent_artwork(rows,0,-1)==2
    assert museum_desk.adjacent_artwork([],0,1)==0


def test_desk_native_thumbnail_and_viewer_navigation(monkeypatch,tmp_path):
    from concurrent.futures import Future
    from types import SimpleNamespace
    rows=[dict(art('aic-'+str(n)),downloaded=True) for n in (1,2)]
    paths={row['id']:tmp_path/(row['id']+'.jpg') for row in rows}
    class Immediate:
        def submit(self,fn,*args,**kwargs):
            f=Future();f.set_result(fn(*args,**kwargs));return f
        def shutdown(self,**kwargs):pass
    native=Mock(enabled=True)
    monkeypatch.setattr(museum_desk,'Background',Immediate)
    monkeypatch.setattr(museum_desk,'NativePreviewController',lambda:native)
    monkeypatch.setattr(museum_desk.sys,'stdin',SimpleNamespace(fileno=lambda:0))
    monkeypatch.setattr(museum_desk.termios,'tcgetattr',lambda fd:[])
    monkeypatch.setattr(museum_desk.termios,'tcsetattr',lambda *a:None)
    monkeypatch.setattr(museum_desk.tty,'setcbreak',lambda fd:None)
    monkeypatch.setattr(museum_desk.shutil,'get_terminal_size',lambda default:__import__('os').terminal_size((100,32)))
    keys=iter(['', 'enter','right','','right','left',' ','esc','q'])
    labels=[]
    monkeypatch.setattr(museum_desk.terminal_style,'command_lines',lambda text,width:labels.append(text) or [text])
    ui=SimpleNamespace(_read_tty_key=lambda *a:next(keys),_ansi_clip=lambda text,width:text[:width],_c=lambda text,color:text)
    client=SimpleNamespace(node='local',snapshot=lambda:{'items':rows},image=lambda row:paths[row['id']])
    assert museum_desk.desk(client,ui)==0
    calls=[call.args for call in native.request.call_args_list]
    assert any(path==paths['aic-1'] and col>1 for path,row,col,h,w in calls)
    assert any(path==paths['aic-2'] and col==1 for path,row,col,h,w in calls)
    assert all('Q quit' not in label and 'I image' not in label for label in labels)
    assert any('q quit' in label and 'W shell pane' in label for label in labels)
    native.close.assert_called_once()


def test_shift_navigation_uses_visible_page_and_bounds():
    for key,expected in [('shiftup',3),('shiftdown',17),('shiftleft',0),('shiftright',19)]:
        assert museum_desk.navigate(10,key,20,7)==expected
    assert museum_desk.navigate(0,'shiftup',20,7)==0
    assert museum_desk.navigate(0,'shiftright',0,7)==0


def test_sorting_dates_and_details():
    rows=[dict(id='1',title='Zebra',artist='Alice',date='18th century'),dict(id='2',title='Apple',artist='Zoe',date='300 B.C.'),dict(id='3',title='Unknown',date='Undated')]
    assert [r['id'] for r in museum_desk.sorted_artworks(rows,'Title')]==['2','3','1']
    assert [r['id'] for r in museum_desk.sorted_artworks(rows,'Artist')]==['1','2','3']
    assert [r['id'] for r in museum_desk.sorted_artworks(rows,'Century')]==['2','1','3']
    assert all(len(line)<=24 for line in museum_desk.artwork_info(rows[0],24))


def test_saver_cache_bounded_verified_and_offline(tmp_path,monkeypatch):
    import museum_cache
    monkeypatch.setattr(Path,'home',lambda:tmp_path)
    monkeypatch.setattr(museum_cache,'MAX_WORKS',2)
    for number in range(1,4):
        row=dict(art('aic-'+str(number)),sha256=museum.hashlib.sha256(JPEG).hexdigest())
        museum_cache.store(row,JPEG,'owner')
    root=museum_cache.folder()
    assert not (root/'aic-1.jpg').exists()
    assert len(json.loads((root/'catalog.json').read_text())['items'])==2
    with pytest.raises(ValueError,match='checksum'):museum_cache.store(row,b'wrong','owner')
    museum_art._checked=0;museum_art._stamp=None
    first= museum_art.artwork(0)[1];second=museum_art.artwork(museum_art.INTERVAL)[1]
    assert first.is_file() and second.is_file() and first!=second
    assert 'ASCII Museum' in player_visuals.NAMES


def test_named_collections_do_not_duplicate_images(tmp_path,monkeypatch):
    m=museum.Museum(tmp_path);monkeypatch.setattr(museum,'detail',lambda ident:art(ident));monkeypatch.setattr(museum,'fetch',lambda *a:JPEG)
    m.save('aic-1');created=m.change({'action':'collection-create','name':'Quiet landscapes'});ident=created['active_collection']
    with pytest.raises(ValueError):m.change({'action':'collection-create','name':'quiet landscapes'})
    m.change({'action':'collection-add','collection':ident,'id':'aic-1'})
    assert m.snapshot()['items'][0]['collections']==[ident]
    assert len(list((tmp_path/'images').glob('*')))==1
    assert museum.Museum(tmp_path).snapshot()['collections'][ident]['name']=='Quiet landscapes'
    m.change({'action':'collection-remove','collection':ident,'id':'aic-1'})
    assert m.snapshot()['items'][0]['collections']==[]


def test_offline_catalog_keeps_metadata_and_reuses_saver_cache(tmp_path,monkeypatch):
    import museum_library,museum_cache
    monkeypatch.setattr(Path,'home',lambda:tmp_path)
    rows=[dict(art('aic-'+str(n)),downloaded=True,sha256=museum.hashlib.sha256(JPEG).hexdigest(),collections=['landscape']) for n in (1,2)]
    museum_library.remember('owner',{'items':rows,'collections':{'landscape':{'name':'Landscapes'}}})
    museum_cache.store(rows[0],JPEG,'owner')
    client=museum_desk.Client('owner');monkeypatch.setattr(client,'request',Mock(side_effect=ValueError('Owner offline')))
    result=client.snapshot()
    assert result['offline'] and len(result['items'])==2 and result['offline_count']==1
    assert client.image(result['items'][0]).is_file()
    assert not result['items'][1]['downloaded']
    assert len(museum_library.view(result['items'],'collections','landscape',True))==1
    assert not museum_library.snapshot('different-owner')['items']


def test_shuffle_contains_every_work_once_and_preserves_input():
    rows=[dict(id=str(n),title=str(n)) for n in range(20)]
    result=museum_desk.sorted_artworks(rows,'Shuffle')
    assert sorted(r['id'] for r in result)==sorted(r['id'] for r in rows)
    assert rows[0]['id']=='0' and result is not rows


def test_node_offline_catalog_and_cached_image(tmp_path,monkeypatch):
    import museum_library
    monkeypatch.setattr(Path,'home',lambda:tmp_path)
    row=dict(art(),downloaded=True)
    museum_library.remember('owner',{'items':[row]});path=museum_library.store_image('owner',row['id'],JPEG)
    h=object.__new__(node.API);h.path='/v1/museum?target=owner';h._file_target=Mock(side_effect=ValueError('Owner offline'));h.sendj=lambda code,value:(code,value)
    code,result=h._museum_request();assert code==200 and result['offline'] and result['items'][0]['available_offline']
    h.path='/v1/museum/image?target=owner&id=aic-1';h._serve_file_range=lambda path,mime:(path,mime)
    assert h._museum_request()[0]==path


def test_featured_queries_use_museum_flags(monkeypatch):
    from urllib.parse import urlsplit,parse_qs
    urls=[]
    def get(url):
        urls.append(url)
        return {'objectIDs':[1,2],'total':45} if 'metmuseum' in url else {'data':[{'id':3}],'pagination':{'total_pages':1}}
    monkeypatch.setattr(museum,'get_json',get)
    assert museum.featured_ids('met',1)==(['met-1','met-2'],True)
    assert parse_qs(urlsplit(urls[-1]).query)['isHighlight']==['true']
    assert museum.featured_ids('aic',1)==(['aic-3'],False)
    params=json.loads(parse_qs(urlsplit(urls[-1]).query)['params'][0])
    assert {'term':{'is_boosted':True}} in params['query']['bool']['filter']
    assert {'term':{'is_public_domain':True}} in params['query']['bool']['filter']


def test_featured_named_collections_reuse_images_and_report_shortfall(tmp_path,monkeypatch):
    m=museum.Museum(tmp_path)
    monkeypatch.setattr(museum,'detail',lambda ident:art(ident))
    fetch=Mock(return_value=JPEG);monkeypatch.setattr(museum,'fetch',fetch)
    monkeypatch.setattr(museum,'featured_ids',lambda source,page:([source+'-1',source+'-1'],False))
    m.save('met-1');m.favorite('met-1')
    m.start_featured(2);m.worker.join(3)
    result=m.snapshot()
    assert result['job']['state']=='partial' and result['job']['saved']==2
    assert result['job']['counts']=={'met':1,'aic':1}
    assert len(result['collections'])==2 and fetch.call_count==2
    assert all(len(row['collections'])==1 for row in result['items'])
    assert next(row for row in result['items'] if row['id']=='met-1')['favorite']
    m.start_featured(1);m.worker.join(3)
    assert m.snapshot()['job']['state']=='complete'
    assert len(m.snapshot()['collections'])==2 and fetch.call_count==2


def test_featured_errors_cancel_and_validation(tmp_path,monkeypatch):
    m=museum.Museum(tmp_path)
    for count in (0,501):
        with pytest.raises(ValueError):m.start_featured(count)
    with pytest.raises(ValueError):m.start_featured(1,'elsewhere')
    def offline(*args):raise OSError('source offline')
    monkeypatch.setattr(museum,'featured_ids',offline)
    m.start_featured(1);m.worker.join(3)
    assert m.snapshot()['job']['state']=='partial' and len(m.snapshot()['job']['errors'])==2
    def cancel(*args):m.stop.set();return ['met-1'],True
    monkeypatch.setattr(museum,'featured_ids',cancel)
    m.start_featured(1,'met');m.worker.join(3)
    assert m.snapshot()['job']['state']=='cancelled'


def test_featured_repeat_reports_active_job(tmp_path):
    m=museum.Museum(tmp_path);state=m.read()
    state['job']={'state':'running','kind':'featured','saved':123,'requested':1000};m.write(state)
    m.worker=Mock();m.worker.is_alive.return_value=True
    result=m.start_featured()
    assert result['job']['saved']==123
    assert m.read()==state


def test_remote_museum_error_preserves_owner_message(monkeypatch):
    import urllib.error
    h=object.__new__(node.API);h.path='/v1/museum?target=owner'
    h._file_target=lambda:({},None);h.sendj=lambda code,value:(code,value)
    monkeypatch.setattr(node,'_copy_route',lambda peer:'https://owner')
    error=urllib.error.HTTPError('https://owner',400,'Bad Request',{},io.BytesIO(b'{"error":"A collection download is already running"}'))
    monkeypatch.setattr(node,'http_json',Mock(side_effect=error))
    code,result=h._museum_request({'action':'featured'})
    assert code==400 and result['error']=='A collection download is already running'


def test_job_progress_truthful_partial_and_bounded():
    text=museum_desk.job_progress({'state':'partial','saved':250,'requested':1000,'counts':{'met':50,'aic':200}},80)
    assert '25%' in text and '250/1000' in text and 'partial' in text
    assert 'met: 50' in text and 'aic: 200' in text
    assert museum_desk.job_progress({})==''
    assert '100%' in museum_desk.job_progress({'state':'complete','saved':1,'requested':1})


def test_removal_grace_undo_expiry_and_no_redownload(tmp_path,monkeypatch):
    m=museum.Museum(tmp_path);m.store(art(),JPEG);m.favorite('aic-1')
    monkeypatch.setattr(museum.time,'time',lambda:1000)
    row=m.mark_removal('aic-1')['items'][0]
    assert row['removal_due']==1000+48*3600 and not row['favorite']
    m.expire_removals(row['removal_due']-1);assert m.image('aic-1').exists()
    m.favorite('aic-1');assert not m.snapshot()['items'][0].get('removal_due')
    row=m.mark_removal('aic-1')['items'][0];m.expire_removals(row['removal_due'])
    assert m.snapshot()['items'][0]['removed_at'] and not m.snapshot()['items'][0]['downloaded']
    with pytest.raises(ValueError,match='undo'):m.save('aic-1')
    m.mark_removal('aic-1');assert not m.snapshot()['items'][0].get('removal_due')


def test_removal_is_owner_local_and_review_is_reversible(tmp_path):
    import museum_library
    row=dict(art(),removal_due=2000)
    m=museum.Museum(tmp_path);m.store(row,JPEG)
    assert not m.snapshot()['items'][0].get('removal_due')
    assert museum_library.view([row])==[]
    assert museum_library.view([row],'review')==[row]


def test_daily_refill_opt_in_limit_and_persistent_schedule(tmp_path,monkeypatch):
    m=museum.Museum(tmp_path);called=Mock();monkeypatch.setattr(m,'_refill',called)
    m.maintain();assert not called.called
    m.rotation(True);m.maintain();m.worker.join(2)
    called.assert_called_once_with(100)
    m.maintain();called.assert_called_once()
    assert m.read()['rotation']['next_check']>time.time()
    m.rotation(False);assert not m.snapshot()['rotation']['enabled']


def test_refill_preserves_rejections_and_existing_records(tmp_path,monkeypatch):
    m=museum.Museum(tmp_path);m.store(art('aic-1'),JPEG);m.mark_removal('aic-1');m.rotation(True)
    monkeypatch.setattr(m,'search',lambda *args:{'items':[art('aic-1'),art('aic-2')]})
    monkeypatch.setattr(museum,'detail',lambda ident:art(ident));monkeypatch.setattr(museum,'fetch',lambda *args:JPEG)
    m._refill(1)
    state=m.read();assert state['items']['aic-1']['removal_due']
    assert state['items']['aic-2']['collection']=='Daily discovery'
    assert state['job']['saved']==1
