"""Catalog paging, stable Gutenberg identity, and platform narration choices."""
import io
import json
from pathlib import Path
from unittest.mock import Mock
from urllib.parse import parse_qs,urlsplit
import pytest
import book_core
import book_audio
import book_speech
from test_books import epub


def feed(count=25,next_link='/ebooks/search.opds/?start_index=26'):
    return ('<feed xmlns="http://www.w3.org/2005/Atom">'
        '<entry><title>Subjects navigation</title><link rel="subsection" href="/ebooks/subjects/search.opds/?query=History"/></entry>'
        +''.join(f'<entry><title>Book {i}</title><link rel="subsection" href="/ebooks/{i+1}.opds"/></entry>' for i in range(count))
        +f'<link rel="next" href="{next_link}"/></feed>').encode()


def test_discovery_search_subject_and_pagination(monkeypatch):
    calls=[]
    monkeypatch.setattr(book_core.urllib.request,'urlopen',lambda url,**kw:(calls.append(url) or io.BytesIO(feed())))
    value=book_core.discover('subject','Science fiction',page=True)
    assert len(value['entries'])==25 and value['next_index']==26
    assert parse_qs(urlsplit(calls[-1]).query)['query']==['s.Science s.fiction']
    book_core.discover('search',query='Virginia Woolf',start_index=26,page=True)
    assert parse_qs(urlsplit(calls[-1]).query)=={'query':['Virginia Woolf'],'start_index':['26']}
    for cursor in ('-1','0','abc','https://example.test',1000001):
        with pytest.raises(ValueError):book_core.discover('popular',start_index=cursor,page=True)
    with pytest.raises(ValueError):book_core.discover('search',query='x'*501)


@pytest.mark.parametrize('link',['https://evil.test/ebooks/search.opds/?start_index=26','/ebooks/search.opds/?start_index=0','/ebooks/search.opds/?start_index=1000001'])
def test_pagination_does_not_proxy_untrusted_links(monkeypatch,link):
    monkeypatch.setattr(book_core.urllib.request,'urlopen',lambda *a,**k:io.BytesIO(feed(next_link=link)))
    assert book_core.discover('popular',page=True)['next_index'] is None


def test_existing_gutenberg_book_returns_without_download_and_survives_rescan(tmp_path,monkeypatch):
    shelf=book_core.Shelf(tmp_path/'state.json',tmp_path/'library')
    row=shelf.import_file(epub(tmp_path/'seed.epub'))
    with shelf.edit() as data:data['entries'][0]['source_url']='https://www.gutenberg.org/cache/epub/123/pg123-images.epub'
    monkeypatch.setattr(book_core.urllib.request,'urlopen',Mock(side_effect=AssertionError('Already owned; must not download')))
    assert shelf.fetch('https://www.gutenberg.org/ebooks/123.opds')['id']==row['id']
    assert shelf.catalog()['entries'][0]['gutenberg_id']=='123'
    assert book_core.gutenberg_id({'title':'Book 123','identifier':'https://example.test/ebooks/123'})==''
    assert book_core.gutenberg_id({'identifier':'http://[broken'})==''
    assert book_core.gutenberg_id({'identifier':'http://www.gutenberg.org/ebooks/123'})=='123'
    # A newly recorded acquisition identity survives changed metadata/stat caches.
    with shelf.edit() as data:data['entries'][0].update(gutenberg_id='123',mtime_ns=0)
    assert shelf.scan()['entries'][0]['gutenberg_id']=='123'


def test_standard_narrators_use_installed_ids_and_keep_saved_selection(tmp_path,monkeypatch):
    monkeypatch.setattr(Path,'home',lambda:tmp_path)
    rows=[{'id':'say:Daniel (English (UK))','locale':'en_GB','engine':'say'},
          {'id':'say:Shelley (English (UK))','locale':'en_GB','engine':'say'}]
    standard=book_speech.standard_voices(rows)
    assert standard['male'] is rows[0] and standard['female'] is rows[1]
    book_speech.preferences(voice=rows[1]['id'])
    assert book_speech.preferred_voice(rows) is rows[1]
    assert book_speech.default_voice(rows) is rows[0]
    assert book_speech.standard_voices([])=={'male':None,'female':None}


def test_piper_female_is_discovered_and_rendered_with_its_own_model(tmp_path,monkeypatch):
    monkeypatch.setattr(Path,'home',lambda:tmp_path)
    root=tmp_path/'.local/share/look/book-speech';(root/'venv/bin').mkdir(parents=True)
    (root/'venv/bin/piper').touch()
    for stem in book_speech.PIPER_MODELS.values():
        (root/(stem+'.onnx')).touch();(root/(stem+'.onnx.json')).touch()
    monkeypatch.setattr(book_speech.book_reader,'binary',lambda name:'/tools/ffmpeg' if name=='ffmpeg' else None)
    rows=book_speech.voices();assert [r['id'] for r in rows]==['piper:alan','piper:alba']
    assert book_speech.standard_voices(rows)['female']['id']=='piper:alba'
    monkeypatch.setattr(book_audio,'_voices',lambda minute:rows)
    calls=[]
    def run(args,**kw):
        calls.append(args);Path(args[-1]).write_bytes(b'generated')
    monkeypatch.setattr(book_audio.subprocess,'run',run)
    book_audio.render('Read me','book',0,0,'piper:alba')
    assert calls[0][calls[0].index('-m')+1].endswith('en_GB-alba-medium.onnx')
    player=book_speech.Speech(rows[1]);launch=Mock();monkeypatch.setattr(player,'launch',launch)
    try:
        player.start('Text')
        assert launch.call_args.args[0][2].endswith('en_GB-alba-medium.onnx')
    finally:player.close()


def test_discovery_api_passes_search_cursor(monkeypatch):
    from core import node
    discover=Mock(return_value={'entries':[{'title':'Book'}],'next_index':51})
    monkeypatch.setattr(book_core,'discover',discover)
    handler=node.API.__new__(node.API)
    handler.path='/v1/books/discover?mode=search&query=Virginia+Woolf&start_index=26'
    handler.sendj=Mock()
    handler._book_content()
    discover.assert_called_once_with('search','',query='Virginia Woolf',start_index='26',page=True)
    assert handler.sendj.call_args.args[1]['next_index']==51


def test_voice_setup_requests_both_models(tmp_path,monkeypatch):
    monkeypatch.setattr(Path,'home',lambda:tmp_path)
    root=tmp_path/'.local/share/look/book-speech';root.mkdir(parents=True)
    calls=[]
    def run(args,**kwargs):
        calls.append(args)
        if 'piper.download_voices' in args:
            for stem in book_speech.PIPER_MODELS.values():
                (root/(stem+'.onnx')).touch();(root/(stem+'.onnx.json')).touch()
    monkeypatch.setattr(book_speech.subprocess,'run',run)
    book_speech.setup_worker()
    assert calls[-1][-2:]==['en_GB-alan-medium','en_GB-alba-medium']
    assert json.loads((root/'setup.json').read_text())['state']=='ready'


def test_browser_gateway_preserves_catalog_query_and_cursor(monkeypatch):
    import book_web
    handler=Mock(path='/api/books/discover?mode=search&query=Jane+Austen&start_index=26&url=https://evil.test',headers={},wfile=io.BytesIO())
    response=io.BytesIO(b'{"entries":[],"next_index":51}');response.status=200;response.headers={'Content-Type':'application/json'}
    calls=[]
    def fetch(request,**kwargs):calls.append(request.full_url);return response
    monkeypatch.setattr(book_web.urllib.request,'urlopen',fetch)
    book_web.handle(handler,'http://127.0.0.1:7332')
    assert parse_qs(urlsplit(calls[0]).query)=={'mode':['search'],'query':['Jane Austen'],'start_index':['26']}
    assert json.loads(handler.wfile.getvalue())['next_index']==51
