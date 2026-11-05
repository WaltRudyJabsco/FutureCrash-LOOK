import json,time
from pathlib import Path
from unittest.mock import Mock
import pytest
import book_core,book_starter,books
from test_books import epub

@pytest.fixture
def shelf(tmp_path):
    s=book_core.Shelf(tmp_path/'shelf.json',tmp_path/'books')
    s.root.mkdir();destination=s.root/'Gutenberg Starter 1000';destination.mkdir()
    epub(destination/'pg123.epub')
    s.scan()
    with s.edit() as d:d['entries'][0]['gutenberg_id']='123'
    return s

def row(s):return s.catalog()['entries'][0]

def test_reject_undo_grace_and_persistent_exclusion(shelf):
    before=row(shelf);shelf.curate('reject',before['id']);pending=row(shelf)
    assert pending['removal_due']>time.time()+47*3600
    assert books.rows_for(shelf.catalog())==[]
    assert len(books.rows_for(shelf.catalog(),shelf='Pending removals'))==1
    assert shelf.purge_rejected(pending['removal_due']-1)==[]
    shelf.curate('restore',before['id']);assert not row(shelf).get('removal_due')
    assert '123' not in shelf.load()['rejected_gutenberg']
    shelf.curate('reject',before['id']);assert shelf.purge_rejected(row(shelf)['removal_due']+1)==['123']
    assert not Path(before['path']).exists() and not shelf.scan()['entries']
    assert '123' in shelf.load()['rejected_gutenberg']

def test_manual_books_and_changed_files_are_preserved(shelf,tmp_path):
    manual=shelf.import_file(epub(tmp_path/'manual.epub',title='My writing'))
    with pytest.raises(ValueError,match='starter'):shelf.curate('reject',manual['id'])
    starter=next(r for r in shelf.catalog()['entries'] if r['gutenberg_id']=='123')
    shelf.curate('reject',starter['id']);Path(starter['path']).write_bytes(b'new author edits')
    with pytest.raises(ValueError,match='changed'):shelf.purge_rejected(time.time()+49*3600)
    assert Path(starter['path']).read_bytes()==b'new author edits'

def test_multiple_collections_survive_rescan(shelf):
    ident=row(shelf)['id'];shelf.curate('collection',name='Empty')
    shelf.curate('collect',ident,'Research');shelf.curate('collect',ident,'Favorites')
    with shelf.edit() as d:d['entries'][0]['mtime_ns']=0
    shelf.scan();assert row(shelf)['collections']==['Favorites','Research']
    assert len(books.rows_for(shelf.catalog(),shelf='Research'))==1
    shelf.curate('collect',ident,'Research',False)
    assert row(shelf)['collections']==['Favorites'] and 'Empty' in shelf.catalog()['collections']
    for name in ('','x'*81,'line\nline'):
        with pytest.raises(ValueError):shelf.curate('collection',name=name)

def test_refill_skips_rejected_and_owned_and_preserves_settings(shelf,tmp_path,monkeypatch):
    monkeypatch.setattr(book_starter,'folder',lambda:tmp_path/'refill')
    book_starter.configure(shelf,True,2)
    with shelf.edit() as d:d['rejected_gutenberg']={'456':{'title':'Rejected'}}
    monkeypatch.setattr(book_starter,'plan',lambda:[{'id':'123','title':'A Book','author':'An Author'},{'id':'456','title':'Rejected','author':'A'},{'id':'789','title':'New','author':'B'}])
    calls=[]
    def fetch(s,r):
        calls.append(r['id']);p=s.root/'Gutenberg Starter 1000'/('pg'+r['id']+'.epub');epub(p,title=r['title']);return p
    monkeypatch.setattr(book_starter,'fetch',fetch)
    result=book_starter.run(shelf)
    assert calls==['789'] and result['added']==1 and len(shelf.catalog()['entries'])==2
    assert '456' in shelf.load()['rejected_gutenberg']
    assert book_starter.run(shelf)['added']==0

def test_disabled_refill_does_not_touch_network(shelf,tmp_path,monkeypatch):
    monkeypatch.setattr(book_starter,'folder',lambda:tmp_path/'refill')
    monkeypatch.setattr(book_starter,'plan',Mock(side_effect=AssertionError('network')))
    assert book_starter.run(shelf)['state']=='disabled'
    for target in (0,10001,True):
        with pytest.raises(ValueError):book_starter.configure(shelf,True,target)

def test_api_curation_dispatch_and_empty_collections(shelf,monkeypatch):
    from core import node
    monkeypatch.setattr(node,'identity',lambda:{'name':'owner'})
    class Handler:
        def _file_target(self):return None,{}
        def _books_shelf(self):return shelf
        def sendj(self,status,value):return status,value
    handler=Handler()
    code,value=node.API._books_request(handler,{'action':'collection','name':'Series'})
    assert code==200 and value['collections']==['Series']
    code,value=node.API._books_request(handler,{'action':'reject','id':row(shelf)['id']})
    assert code==200 and value['book']['removal_due']
    code,value=node.API._books_request(handler,{'action':'refill','enabled':True,'target':1000})
    assert code==200 and value['refill']['enabled']

def test_refill_one_worker_and_offline_media(shelf,tmp_path,monkeypatch):
    import fcntl
    root=tmp_path/'worker';root.mkdir();monkeypatch.setattr(book_starter,'folder',lambda:root)
    with (root/'refill.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        assert book_starter.run(shelf)['state']=='running'
    absent=book_core.Shelf(tmp_path/'absent.json',tmp_path/'unmounted')
    assert book_starter.run(absent)['state']=='offline' and not absent.root.exists()

def test_daily_refill_is_opt_in_and_throttled(shelf,monkeypatch):
    monkeypatch.setattr(book_starter.book_core,'Shelf',lambda:shelf)
    start=Mock();monkeypatch.setattr(book_starter.subprocess,'Popen',start)
    book_starter.tick();start.assert_not_called()
    book_starter.configure(shelf,True,1000)
    book_starter.tick();book_starter.tick();assert start.call_count==1


def test_changed_book_stays_protected_after_rescan(shelf):
    original=row(shelf);shelf.curate('reject',original['id'])
    epub(Path(original['path']),title='My annotations and changes')
    shelf.scan()
    with pytest.raises(ValueError,match='changed'):shelf.purge_rejected(time.time()+49*3600)
    assert Path(original['path']).exists()


def test_download_checks_public_domain_and_publishes_valid_epub(shelf,tmp_path,monkeypatch):
    import io,zipfile
    source=epub(tmp_path/'source.epub',title='New book')
    with zipfile.ZipFile(source) as z:contents={name:z.read(name) for name in z.namelist()}
    contents['OPS/book.opf']=contents['OPS/book.opf'].replace(b'</metadata>',b'<dc:rights>Public domain in the USA.</dc:rights></metadata>')
    with zipfile.ZipFile(source,'w') as z:
        for name,data in contents.items():z.writestr(name,data)
    monkeypatch.setattr(book_starter.time,'sleep',lambda _:None)
    monkeypatch.setattr(book_starter.urllib.request,'urlopen',lambda *a,**k:io.BytesIO(source.read_bytes()))
    path=book_starter.fetch(shelf,{'id':'789'})
    assert book_core.metadata(path)['title']=='New book'
    epub(source,title='Missing license')
    with pytest.raises(ValueError,match='public-domain'):book_starter.fetch(shelf,{'id':'790'})
    assert not (path.parent/'pg790.epub').exists()
    assert not list(path.parent.glob('*.part'))


def test_favorites_leave_pool_survive_scan_and_restore_rejection(shelf):
    ident=row(shelf)['id'];shelf.curate('reject',ident)
    shelf.curate('favorite',ident,selected=True)
    assert not row(shelf).get('removal_due') and '123' not in shelf.load()['rejected_gutenberg']
    assert books.rows_for(shelf.catalog())==[]
    assert len(books.rows_for(shelf.catalog(),shelf='Favorites'))==1
    assert len(books.rows_for(shelf.catalog(),shelf='All'))==1
    shelf.scan();assert row(shelf)['favorite']
    shelf.curate('favorite',ident,selected=False)
    assert len(books.rows_for(shelf.catalog()))==1
    shelf.curate('favorite',ident,selected=True);shelf.curate('reject',ident)
    assert not row(shelf)['favorite']


def test_refill_preserves_favorites_and_counts_only_undecided(shelf,tmp_path,monkeypatch):
    monkeypatch.setattr(book_starter,'folder',lambda:tmp_path/'refill')
    saved=row(shelf);shelf.curate('favorite',saved['id'],selected=True)
    book_starter.configure(shelf,True,1)
    monkeypatch.setattr(book_starter,'plan',lambda:[{'id':'123','title':'A Book','author':'An Author'},{'id':'789','title':'Fresh','author':'B'}])
    calls=[]
    def fetch(s,r):
        calls.append(r['id']);return epub(s.root/'Gutenberg Starter 1000'/('pg'+r['id']+'.epub'),title=r['title'])
    monkeypatch.setattr(book_starter,'fetch',fetch)
    assert book_starter.run(shelf)['added']==1
    assert calls==['789'] and len(shelf.load()['entries'])==2
    assert book_starter.pool_count(shelf.load())==1
    assert Path(saved['path']).exists()
    assert book_starter.run(shelf)['added']==0
