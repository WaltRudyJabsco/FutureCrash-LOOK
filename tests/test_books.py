import io
import json
from pathlib import Path
import threading
import urllib.request
import zipfile

import pytest
import book_core
import books
from core import node,ingress
from test_media_request_regressions import lk


def epub(path,title='A Book',author='An Author'):
    with zipfile.ZipFile(path,'w') as archive:
        archive.writestr('mimetype','application/epub+zip')
        archive.writestr('META-INF/container.xml','<container><rootfiles><rootfile full-path="OPS/book.opf"/></rootfiles></container>')
        archive.writestr('OPS/book.opf',f'<package xmlns:dc="http://purl.org/dc/elements/1.1/"><metadata><dc:title>{title}</dc:title><dc:creator>{author}</dc:creator></metadata></package>')
    return path


def test_import_preserves_bytes_reads_metadata_and_keeps_edits(tmp_path):
    source=epub(tmp_path/'original.epub','Café &amp; Books','Zoë')
    before=source.read_bytes();shelf=book_core.Shelf(tmp_path/'state.json',tmp_path/'library')
    row=shelf.import_file(source)
    assert row['title']=='Café & Books' and row['author']=='Zoë'
    assert Path(row['path']).read_bytes()==before==source.read_bytes()
    ident=row['id'];shelf.update(ident,{'title':'Edited','status':'Reading','shelf':'Research','position':'Chapter 3'})
    shelf.scan();edited=shelf.catalog()['entries'][0]
    assert edited['id']==ident and edited['title']=='Edited' and edited['position']=='Chapter 3'
    assert source.exists() and Path(row['path']).read_bytes()==before
    assert len(shelf.import_file(source)['id'])==64
    assert len(shelf.catalog()['entries'])==1
    Path(row['path']).unlink();assert shelf.scan()['entries']==[]


def test_import_never_overwrites_a_different_book(tmp_path):
    shelf=book_core.Shelf(tmp_path/'state.json',tmp_path/'library')
    source=epub(tmp_path/'book.epub');row=shelf.import_file(source)
    old=Path(row['path']).read_bytes();epub(source,'Different book')
    with pytest.raises(FileExistsError):shelf.import_file(source)
    assert Path(row['path']).read_bytes()==old


def test_dedicated_root_and_bad_metadata_are_bounded(tmp_path):
    root=tmp_path/'library';root.mkdir();outside=epub(tmp_path/'outside.epub')
    (root/'symlink.epub').symlink_to(outside)
    broken=root/'broken.epub';broken.write_bytes(b'not a zip')
    shelf=book_core.Shelf(tmp_path/'state.json',root)
    value=shelf.scan();assert value['entries']==[] and len(value['warnings'])==1
    with pytest.raises(ValueError):book_core.xml(b'<!DOCTYPE x [<!ENTITY x "evil">]><x/>')
    with pytest.raises(ValueError):book_core.metadata(broken)
    with pytest.raises(ValueError):shelf.update('missing',{'path':'/elsewhere'})


def test_configuration_uses_owner_books_folder_without_creating_it(tmp_path,monkeypatch):
    monkeypatch.setattr(Path,'home',lambda:tmp_path)
    config=tmp_path/'.config/look/media_library.json';config.parent.mkdir(parents=True)
    config.write_text(json.dumps({'root':str(tmp_path/'storage/media')}))
    shelf=book_core.Shelf()
    assert shelf.root==tmp_path/'storage/media/books' and not shelf.root.exists()
    assert shelf.catalog()['entries']==[]


def test_public_catalog_keeps_detail_links_for_lazy_acquisition(monkeypatch):
    atom=b'<feed xmlns="http://www.w3.org/2005/Atom"><entry><title>Book</title><author><name>Writer</name></author><link type="application/atom+xml;profile=opds-catalog" rel="subsection" href="/ebooks/123.opds"/></entry></feed>'
    monkeypatch.setattr(book_core.urllib.request,'urlopen',lambda *a,**kw:io.BytesIO(atom))
    assert book_core.gutenberg('Book')==[{'title':'Book','author':'Writer','url':'https://www.gutenberg.org/ebooks/123.opds'}]


def test_download_resolves_opds_and_verifies_book(tmp_path,monkeypatch):
    source=epub(tmp_path/'seed.epub');payload=source.read_bytes()
    atom=b'<entry xmlns="http://www.w3.org/2005/Atom"><link type="application/epub+zip" rel="http://opds-spec.org/acquisition" href="https://www.gutenberg.org/book.epub"/></entry>'
    class Response(io.BytesIO):
        url='https://www.gutenberg.org/book.epub'
    calls=[]
    def open_url(url,**kw):
        calls.append(url)
        return io.BytesIO(atom) if isinstance(url,str) and url.endswith('.opds') else Response(payload)
    monkeypatch.setattr(book_core.urllib.request,'urlopen',open_url)
    shelf=book_core.Shelf(tmp_path/'state.json',tmp_path/'library')
    row=shelf.fetch('https://www.gutenberg.org/ebooks/123.opds')
    assert Path(row['path']).read_bytes()==payload and len(calls)==2
    assert row['source_url']=='https://www.gutenberg.org/book.epub'
    with pytest.raises(ValueError):shelf.fetch('file:///etc/passwd')
    assert not list(shelf.root.glob('.download-*'))
    assert len(shelf.catalog()['entries'])==1 and all(Path(r['path']).exists() for r in shelf.catalog()['entries'])


def test_shelf_search_state_and_notes_links():
    row={'id':'one','title':'Book [one]','author':'Zoë','format':'EPUB','status':'Reading','shelf':'Research','node':'owner','path':'/Books/My Book.epub'}
    assert books.rows_for({'entries':[row]},'zoë','Research')==[row]
    assert books.rows_for({'entries':[row]},'', 'Finished')==[]
    from notebook_markdown import extract_links
    link=books.make_link(row['title'],'@owner:'+row['path'])
    assert extract_links(link)[0][1]=='@owner:/Books/My Book.epub'


def test_book_transfer_uses_owner_not_matching_local_path(tmp_path,monkeypatch):
    source=epub(tmp_path/'source.epub');ident=book_core.digest(source)
    monkeypatch.setattr(Path,'home',lambda:tmp_path)
    monkeypatch.setattr(books.fabric_files,'request',lambda *a,**kw:{'identity':{'name':'this-node'}})
    urls=[]
    def fetch(url,**kw):urls.append(url);return io.BytesIO(source.read_bytes())
    monkeypatch.setattr(books.urllib.request,'urlopen',fetch)
    result=books.local_copy({'id':ident,'node':'other-node','path':str(source)})
    assert result!=source and result.read_bytes()==source.read_bytes()
    assert 'target=other-node' in urls[0]
    assert books.local_copy({'id':ident,'node':'other-node','path':str(source)})==result and len(urls)==1


def test_books_api_catalog_range_and_unknown_id(tmp_path,monkeypatch):
    shelf=book_core.Shelf(tmp_path/'state.json',tmp_path/'library');row=shelf.import_file(epub(tmp_path/'seed.epub'))
    monkeypatch.setattr(node.API,'_books_shelf',lambda self:shelf)
    monkeypatch.setattr(node,'identity',lambda:{'name':'owner'})
    server=node.FabricHTTPServer(('127.0.0.1',0),node.API,plane='local')
    threading.Thread(target=server.serve_forever,daemon=True).start()
    base=f'http://127.0.0.1:{server.server_port}'
    try:
        with urllib.request.urlopen(base+'/v1/books') as response:value=json.load(response)
        assert value['entries'][0]['title']=='A Book' and value['entries'][0]['node']=='owner'
        for payload in ({'action':'scan'},{'action':'update','id':row['id'],'fields':{'status':'Reading','title':'Edited title'}}):
            request=urllib.request.Request(base+'/v1/books',data=json.dumps(payload).encode())
            with urllib.request.urlopen(request) as response:assert json.load(response)['ok']
        assert shelf.catalog()['entries'][0]['title']=='Edited title'
        assert Path(row['path']).read_bytes()==(tmp_path/'seed.epub').read_bytes()
        request=urllib.request.Request(base+'/v1/books/item?id='+row['id'],headers={'Range':'bytes=0-3'})
        with urllib.request.urlopen(request) as response:
            assert response.status==206 and response.read()==b'PK\x03\x04'
        with pytest.raises(urllib.error.HTTPError) as error:urllib.request.urlopen(base+'/v1/books/item?id=../../etc/passwd')
        assert error.value.code==404
    finally:server.shutdown();server.server_close()
    assert ingress._is_stream_path('/v1/books/item')


def test_books_alias_and_ui_escape_restore_terminal(lk,monkeypatch,tmp_path):
    import subprocess,sys
    root=Path(__file__).resolve().parents[1]
    for command in ('books','bk'):
        output=subprocess.check_output([sys.executable,str(root/'look/lk'),command,'--help'],text=True)
        assert 'shelf' in output.casefold()
    monkeypatch.setattr(books,'catalog',lambda:{'entries':[]})
    monkeypatch.setattr(books.media_storage,'settings',lambda:{'node':'local'})
    monkeypatch.setattr(books.termios,'tcgetattr',lambda fd:[])
    restored=[];monkeypatch.setattr(books.termios,'tcsetattr',lambda *a:restored.append(1));monkeypatch.setattr(books.tty,'setcbreak',lambda *a:None)
    class Input:
        def fileno(self):return 0
    monkeypatch.setattr(books.sys,'stdin',Input())
    monkeypatch.setattr(lk,'_read_tty_key',lambda *a:'esc')
    assert books.desk(lk)==0 and restored


def test_books_ui_search_and_copy_link_with_unicode(lk,monkeypatch):
    row={'id':'1','node':'owner','path':'/Books/My Book.epub','title':'Café Book','author':'Zoë','format':'EPUB','status':'To Read'}
    monkeypatch.setattr(books,'catalog',lambda:{'entries':[row]})
    monkeypatch.setattr(books.media_storage,'settings',lambda:{'node':'local'})
    monkeypatch.setattr(books.termios,'tcgetattr',lambda fd:[])
    monkeypatch.setattr(books.termios,'tcsetattr',lambda *a:None)
    monkeypatch.setattr(books.tty,'setcbreak',lambda *a:None)
    class Input:
        def fileno(self):return 0
    monkeypatch.setattr(books.sys,'stdin',Input())
    keys=iter(['/','C','a','up','f','é','paste: Book\n','\n','y','esc','esc'])
    monkeypatch.setattr(lk,'_read_tty_key',lambda *a:next(keys))
    links=[];monkeypatch.setattr(books.look_renderer,'copy_text',lambda value:links.append(value))
    assert books.desk(lk)==0
    assert len(links)==1 and '@owner:/Books/My Book.epub' in links[0]


def test_same_book_rename_preserves_reading_state_and_duplicates_edit_together(tmp_path):
    shelf=book_core.Shelf(tmp_path/'state.json',tmp_path/'library')
    row=shelf.import_file(epub(tmp_path/'one.epub'))
    shelf.update(row['id'],{'status':'Reading','position':'p. 9'})
    Path(row['path']).rename(shelf.root/'two.epub')
    value=shelf.scan();assert value['entries'][0]['position']=='p. 9'
    import shutil
    shutil.copyfile(shelf.root/'two.epub',shelf.root/'three.epub');shelf.scan()
    shelf.update(row['id'],{'title':'Renamed title'})
    assert all(r['title']=='Renamed title' for r in shelf.catalog()['entries'])


def test_interactive_owner_override_reaches_shelf(monkeypatch):
    class Terminal:
        def isatty(self):return True
    monkeypatch.setattr(books.sys,'stdin',Terminal());monkeypatch.setattr(books.sys,'stdout',Terminal())
    seen=[];monkeypatch.setattr(books,'desk',lambda ui,query,owner:seen.append(owner) or 0)
    assert books.main(['--node','chosen-owner'],object())==0
    assert seen==['chosen-owner']


@pytest.mark.parametrize('kitty',[False,True])
def test_books_clears_text_and_native_graphics_before_catalog_load(lk,monkeypatch,capsys,kitty):
    if kitty:monkeypatch.setenv('KITTY_WINDOW_ID','test')
    else:
        monkeypatch.delenv('KITTY_WINDOW_ID',raising=False);monkeypatch.setenv('TERM','xterm-256color')
    def catalog():
        startup=capsys.readouterr().out
        assert '\x1b[2J\x1b[H' in startup and 'opening shelf' in startup
        assert ('\x1b_Ga=d,d=a,q=2\x1b\\' in startup)==kitty
        return {'entries':[]}
    monkeypatch.setattr(books,'catalog',catalog)
    monkeypatch.setattr(books.termios,'tcgetattr',lambda fd:[])
    monkeypatch.setattr(books.termios,'tcsetattr',lambda *a:None)
    monkeypatch.setattr(books.tty,'setcbreak',lambda *a:None)
    class Input:
        def fileno(self):return 0
    monkeypatch.setattr(books.sys,'stdin',Input())
    monkeypatch.setattr(lk,'_read_tty_key',lambda *a:'esc')
    assert books.desk(lk,owner='library-server')==0
    assert 'import to library-server' in capsys.readouterr().out
