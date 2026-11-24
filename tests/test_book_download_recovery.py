"""Bounded public Gutenberg recovery; never mirror arbitrary URLs or duplicate IDs."""
import io
from pathlib import Path
import urllib.error
from unittest.mock import Mock
import pytest
import book_core
from test_books import epub


@pytest.mark.parametrize('entry_url',['https://www.gutenberg.org/ebooks/72086.epub.images','https://www.gutenberg.org/ebooks/72086.opds'])
def test_gutenberg_outage_uses_fixed_mirror_and_is_idempotent(tmp_path,monkeypatch,entry_url):
    raw=epub(tmp_path/'source.epub',title='Gay-Neck').read_bytes();calls=[]
    class Response(io.BytesIO):url=book_core.GUTENBERG_MIRROR+'/72086/pg72086-images.epub'
    def fetch(request,**kw):
        url=request if isinstance(request,str) else request.full_url;calls.append(url)
        if url.startswith('https://www.gutenberg.org/'):
            raise urllib.error.HTTPError(url,503,'Maintenance',{},None)
        assert url==Response.url
        return Response(raw)
    monkeypatch.setattr(book_core.urllib.request,'urlopen',fetch)
    shelf=book_core.Shelf(tmp_path/'books.json',tmp_path/'library')
    row=shelf.fetch(entry_url)
    assert row['title']=='Gay-Neck' and row['gutenberg_id']=='72086'
    assert Path(row['path']).read_bytes()==raw and row['source_url']==entry_url
    assert len(calls)==2
    calls.clear();assert shelf.fetch(entry_url)['id']==row['id'] and not calls
    assert len(shelf.catalog()['entries'])==1


def test_fallback_tries_text_edition_if_mirror_has_no_images(tmp_path,monkeypatch):
    raw=epub(tmp_path/'source.epub').read_bytes();calls=[]
    class Response(io.BytesIO):url=book_core.GUTENBERG_MIRROR+'/123/pg123-noimages.epub'
    def fetch(request,**kw):
        url=request.full_url;calls.append(url)
        if url==Response.url:return Response(raw)
        raise urllib.error.HTTPError(url,503 if 'www.gutenberg' in url else 404,'Unavailable',{},None)
    monkeypatch.setattr(book_core.urllib.request,'urlopen',fetch)
    shelf=book_core.Shelf(tmp_path/'books.json',tmp_path/'library')
    assert shelf.fetch('https://www.gutenberg.org/ebooks/123.epub.images')['gutenberg_id']=='123'
    assert len(calls)==3


@pytest.mark.parametrize('url,code',[('https://example.test/book.epub',503),('https://www.gutenberg.org/ebooks/123.epub.images',404)])
def test_unrelated_downloads_and_missing_records_are_not_mirrored(tmp_path,monkeypatch,url,code):
    fetch=Mock(side_effect=urllib.error.HTTPError(url,code,'Unavailable',{},None))
    monkeypatch.setattr(book_core.urllib.request,'urlopen',fetch)
    shelf=book_core.Shelf(tmp_path/'books.json',tmp_path/'library')
    with pytest.raises(urllib.error.HTTPError):shelf.fetch(url)
    fetch.assert_called_once();assert shelf.catalog()['entries']==[]
    assert not list(shelf.root.glob('.download-*'))


def test_mirror_garbage_never_publishes_a_book(tmp_path,monkeypatch):
    class Response(io.BytesIO):url=book_core.GUTENBERG_MIRROR+'/123/pg123-images.epub'
    def fetch(request,**kw):
        if 'www.gutenberg' in request.full_url:raise urllib.error.HTTPError(request.full_url,503,'Down',{},None)
        return Response(b'not an EPUB')
    monkeypatch.setattr(book_core.urllib.request,'urlopen',fetch)
    shelf=book_core.Shelf(tmp_path/'books.json',tmp_path/'library')
    with pytest.raises(ValueError,match='not an EPUB'):shelf.fetch('https://www.gutenberg.org/ebooks/123.epub.images')
    assert not shelf.catalog()['entries'] and not list(shelf.root.glob('*'))
