import io
import json
from pathlib import Path
import subprocess
import threading
import urllib.request
import urllib.error
import zipfile
from unittest.mock import Mock
import pytest
import book_audio
import book_core
import book_cover
import book_preview
from core import node,ingress
import book_web
from test_book_speech import fixture
from test_media_request_regressions import lk
from test_browser_fabric_views import load

ROOT=Path(__file__).resolve().parents[1]


def library(tmp_path):
    source=fixture(tmp_path/'seed.epub')
    with zipfile.ZipFile(source,'a') as z:
        # A real EPUB3 cover entry, separate from the readable spine.
        opf=z.read('OPS/book.opf').decode().replace('<manifest>','<manifest><item id="cover" href="cover.png" media-type="image/png" properties="cover-image"/>')
        # Rebuild to avoid ambiguous duplicate ZIP member names.
        contents={n:z.read(n) for n in z.namelist() if n!='OPS/book.opf'}
    with zipfile.ZipFile(source,'w') as z:
        for name,data in contents.items():z.writestr(name,data)
        z.writestr('OPS/book.opf',opf);z.writestr('OPS/cover.png',b'\x89PNG\r\n\x1a\ncover')
    shelf=book_core.Shelf(tmp_path/'state.json',tmp_path/'library')
    return shelf,shelf.import_file(source)


def test_reading_identity_survives_rename_and_rescan(tmp_path):
    shelf,row=library(tmp_path)
    shelf.progress(row['id'],{'chapter':1,'paragraph':1,'offset':3.5})
    Path(row['path']).rename(shelf.root/'renamed.epub');shelf.scan()
    assert shelf.catalog()['entries'][0]['reading']['offset']==3.5
    assert shelf.progress(row['id'])['chapter']==1
    with pytest.raises(ValueError):shelf.progress(row['id'],{'offset':float('nan')})
    with pytest.raises(ValueError):shelf.progress(row['id'],{'chapter':-1})
    with pytest.raises(FileNotFoundError):shelf.progress('unknown',{'chapter':0})


def test_cover_extracts_embedded_bytes_and_no_book_download(tmp_path,monkeypatch):
    monkeypatch.setattr(Path,'home',lambda:tmp_path)
    shelf,row=library(tmp_path)
    image=book_cover.cover(row['path'],row['id'])
    assert image.read_bytes().endswith(b'cover')
    monkeypatch.setattr(book_cover.zipfile,'ZipFile',Mock(side_effect=AssertionError('cover must be cached')))
    assert book_cover.cover(row['path'],row['id'])==image
    monkeypatch.setattr(book_cover,'catalog_cover',lambda url:image)
    assert book_preview.image({'url':'https://www.gutenberg.org/ebooks/123.opds'})==image


def test_catalog_cover_rejects_external_and_private_locations():
    for url in ('file:///etc/passwd','https://127.0.0.1/ebooks/1.opds','https://www.gutenberg.org/elsewhere','http://www.gutenberg.org/ebooks/1.opds'):
        assert book_cover.catalog_cover(url) is None
    redirect=book_cover.GutenbergRedirect()
    with pytest.raises(ValueError):redirect.redirect_request(None,None,302,'',{},'http://127.0.0.1/private')


def test_discovery_uses_official_sorting_and_lazy_entry_links(monkeypatch):
    atom=b'<feed xmlns="http://www.w3.org/2005/Atom"><entry><title>Book</title><link rel="subsection" href="/ebooks/123.opds"/><link rel="http://opds-spec.org/image" href="data:image/png;base64,AAAA"/></entry></feed>'
    calls=[]
    def fetch(url,**kw):calls.append(url);return io.BytesIO(atom)
    monkeypatch.setattr(book_core.urllib.request,'urlopen',fetch)
    assert book_core.discover('popular')[0]['url'].endswith('/123.opds')
    assert 'sort_order=downloads' in calls[-1]
    assert 'cover_url' not in book_core.discover('new')[0]
    assert 'sort_order=release_date' in calls[-1]
    assert len(book_core.discover('surprise'))==1
    assert book_core.discover('subjects')[0]['kind']=='subject'
    with pytest.raises(ValueError):book_core.discover('subject','arbitrary')


def test_narration_is_file_only_cached_and_no_speaker_launch(tmp_path,monkeypatch):
    monkeypatch.setattr(Path,'home',lambda:tmp_path)
    voice={'id':'say:Daniel','name':'Daniel','engine':'say'}
    monkeypatch.setattr(book_audio.book_speech,'voices',lambda:[voice])
    monkeypatch.setattr(book_audio.book_speech.book_reader,'binary',lambda name:'/tools/'+name)
    calls=[]
    def run(args,**kw):
        calls.append(args)
        assert kw['stdin']==subprocess.DEVNULL and kw['timeout']<=120
        target=Path(args[args.index('-o')+1]) if args[0].endswith('/say') else Path(args[-1])
        target.write_bytes(b'generated audio')
    monkeypatch.setattr(book_audio.subprocess,'run',run)
    path=book_audio.render('Café $(never shell)', 'book',0,0)
    assert path.read_bytes()==b'generated audio'
    assert '-o' in calls[0] and '-movflags' in calls[1]
    assert book_audio.render('Café $(never shell)', 'book',0,0)==path and len(calls)==2
    with pytest.raises(ValueError):book_audio.passage([{'paragraphs':['one']}],0,1)


def test_books_read_progress_audio_range_and_cover_api(tmp_path,monkeypatch):
    monkeypatch.setattr(Path,'home',lambda:tmp_path)
    shelf,row=library(tmp_path)
    monkeypatch.setattr(node.API,'_books_shelf',lambda self:shelf)
    monkeypatch.setattr(node,'identity',lambda:{'name':'owner'})
    audio=tmp_path/'passage.m4a';audio.write_bytes(b'0123456789')
    monkeypatch.setattr(book_audio,'render',lambda *a:audio)
    server=node.FabricHTTPServer(('127.0.0.1',0),node.API,plane='local')
    threading.Thread(target=server.serve_forever,daemon=True).start()
    base=f'http://127.0.0.1:{server.server_port}'
    try:
        payload={'action':'progress','id':row['id'],'fields':{'chapter':1,'paragraph':1,'offset':2}}
        request=urllib.request.Request(base+'/v1/books',data=json.dumps(payload).encode(),headers={'Content-Type':'application/json'})
        with urllib.request.urlopen(request) as response:assert json.load(response)['reading']['offset']==2
        with urllib.request.urlopen(base+'/v1/books/read?id='+row['id']) as response:value=json.load(response)
        assert value['chapter']==1 and value['paragraph']==1 and value['text']=='Another passage.'
        assert value['chapters'][0]['paragraphs']==3
        request=urllib.request.Request(base+'/v1/books/audio?id='+row['id'],headers={'Range':'bytes=2-5'})
        with urllib.request.urlopen(request) as response:assert response.status==206 and response.read()==b'2345'
        with urllib.request.urlopen(base+'/v1/books/cover?id='+row['id']) as response:assert response.read().endswith(b'cover')
        payload['fields']['paragraph']=999
        request=urllib.request.Request(base+'/v1/books',data=json.dumps(payload).encode())
        with pytest.raises(urllib.error.HTTPError):urllib.request.urlopen(request)
        assert shelf.progress(row['id'])['paragraph']==1
    finally:server.shutdown();server.server_close()
    assert ingress._is_stream_path('/v1/books/audio')
    assert ingress._request_timeout('/v1/books/audio','GET',None,True)>=180


@pytest.mark.parametrize('surface',['signal-window','albert'])
def test_browser_books_requires_auth_for_page_json_and_audio(surface,monkeypatch):
    module=load(surface)
    for path in ('/books','/api/books','/api/books/audio?id=one'):
        handler=module.Handler.__new__(module.Handler);handler.path=path
        handler._require_endpoint=Mock(return_value=False)
        handler.headers={}
        handler.wfile=io.BytesIO()
        gateway=Mock();monkeypatch.setattr(book_web,'handle',gateway)
        handler.do_GET()
        handler._require_endpoint.assert_called_once_with('lo.use');gateway.assert_not_called()
        handler._require_endpoint=Mock(return_value=True)
        handler.send_response=Mock();handler.send_header=Mock();handler.end_headers=Mock()
        handler.do_GET()
        if path=='/books':assert b'books-app' in handler.wfile.getvalue()
        else:gateway.assert_called_once()


def test_browser_book_commands_preserve_note_requests():
    code=(ROOT/'signal-window/browser-views.js').read_text()
    script="const assert=require('node:assert/strict');global.location={href:'https://example.test/'};"+code+'''
const v=FabricBrowserViews;
assert.equal(v.booksCommand('/books').resume,false);
assert.equal(v.booksCommand('Continue reading').resume,true);
assert.equal(v.booksCommand('Read The Great Gatsby').query,'The Great Gatsby');
assert.equal(v.booksCommand('Continue Gatsby').query,'Gatsby');
assert.equal(v.booksCommand('read my notes'),null);
assert.equal(v.booksCommand('play music'),null);
assert.equal(v.booksCommand('continue with the plan'),null);
'''
    subprocess.run(['node','-e',script],check=True)


def test_terminal_preview_keeps_ascii_and_idle_frames_do_not_flicker(tmp_path,monkeypatch,lk,capsys):
    import books
    row={'id':'book','title':'Cover Book','author':'Writer','path':'/books/test.epub','node':'local'}
    monkeypatch.setattr(books,'catalog',lambda:{'entries':[row]})
    monkeypatch.setattr(books.termios,'tcgetattr',lambda fd:[])
    monkeypatch.setattr(books.termios,'tcsetattr',lambda *args:None)
    monkeypatch.setattr(books.tty,'setcbreak',lambda fd:None)
    monkeypatch.setattr(books.sys,'stdin',Mock(fileno=lambda:0))
    import os
    monkeypatch.setattr(lk.shutil,'get_terminal_size',lambda *args:os.terminal_size((110,32)))
    work=Mock();work.get.return_value=(['COVER PREVIEW'],tmp_path/'cover.png')
    monkeypatch.setattr(books,'LatestWork',lambda:work)
    native=Mock(enabled=True);monkeypatch.setattr(books.look_renderer,'NativePreviewController',lambda:native)
    keys=iter(['','M','','esc']);monkeypatch.setattr(lk,'_read_tty_key',lambda *args:next(keys))
    assert books.desk(lk,owner='local')==0
    text=capsys.readouterr().out
    assert 'COVER PREVIEW' in text and 'ASCII previews' in lk._strip_ansi(text)
    assert native.request.call_count==2  # Initial frame and one idle tick; no calls after M.
    assert native.frame_cleared.call_count<=4
    work.close.assert_called_once()


def test_terminal_speech_uses_owner_progress_and_publishes_paragraphs(tmp_path,monkeypatch,lk):
    import book_speech
    source=fixture(tmp_path/'book.epub')
    monkeypatch.setattr(Path,'home',lambda:tmp_path)
    monkeypatch.setattr(book_speech,'voices',lambda:[{'id':'say:Daniel','name':'Daniel','engine':'say'}])
    monkeypatch.setattr(book_speech.sys,'stdin',Mock(fileno=lambda:0))
    monkeypatch.setattr(lk,'_read_tty_key',lambda *args:'esc')
    publish=Mock()
    book_speech.desk(lk,source,reading={'chapter':1,'paragraph':1},save_reading=publish)
    assert publish.call_args.args[0]=={'chapter':1,'paragraph':1,'offset':0,'finished':False}



def test_managed_update_waits_for_narration_preparation(monkeypatch):
    from core import maintenance
    monkeypatch.setattr(maintenance,'local_json',lambda path:{'narration_busy':True} if path=='/v1/books/reader' else {'jobs':[]})
    assert maintenance.imports_active()
