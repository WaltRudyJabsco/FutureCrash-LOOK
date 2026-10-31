"""Bounded book covers: embedded EPUB art, PDF first page and public catalog art."""
from pathlib import Path
import hashlib
import os
import posixpath
import re
import shutil
import subprocess
import tempfile
import urllib.parse
import urllib.request
import zipfile
import book_core

MAX_COVER_BYTES = 8*1024*1024


def cover(path, ident):
    folder=Path.home()/'.cache/look/book-covers';folder.mkdir(parents=True,exist_ok=True)
    out=folder/(ident+'.png')
    for suffix in ('.png','.jpg','.webp'):
        cached=out.with_suffix(suffix)
        if cached.is_file():return cached
    path=Path(path)
    if path.suffix.casefold()=='.pdf':
        helper=shutil.which('pdftoppm')
        if not helper:return None
        with tempfile.TemporaryDirectory(dir=folder) as temp:
            base=Path(temp)/'page'
            subprocess.run([helper,'-f','1','-singlefile','-scale-to','800','-png',str(path),str(base)],stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=10,check=True)
            base.with_suffix('.png').replace(out)
        return out
    with zipfile.ZipFile(path) as archive:
        def read(name,limit):
            info=archive.getinfo(name)
            if info.file_size>limit:raise ValueError('Book cover metadata/image too large')
            return archive.read(info)
        container=book_core.xml(read('META-INF/container.xml',book_core.MAX_METADATA_BYTES))
        package=next(n.get('full-path') for n in container.iter() if n.tag.endswith('rootfile'))
        opf=book_core.xml(read(package,book_core.MAX_METADATA_BYTES))
        old_id=next((n.get('content') for n in opf.iter() if n.tag.endswith('meta') and n.get('name')=='cover'),None)
        image=next((n for n in opf.iter() if n.tag.endswith('item') and ('cover-image' in n.get('properties','').split() or (old_id and n.get('id')==old_id))),None)
        if image is None:return None
        suffix={'image/png':'.png','image/jpeg':'.jpg','image/webp':'.webp'}.get(image.get('media-type'))
        if not suffix:return None
        name=posixpath.normpath(posixpath.join(posixpath.dirname(package),urllib.parse.unquote(image.get('href',''))))
        if name.startswith(('../','/')):raise ValueError('Invalid cover path')
        out=folder/(ident+suffix)
        if not out.is_file():
            data=read(name,MAX_COVER_BYTES)
            fd,temp=tempfile.mkstemp(dir=folder)
            try:
                with os.fdopen(fd,'wb') as stream:stream.write(data)
                os.replace(temp,out)
            finally:Path(temp).unlink(missing_ok=True)
        return out


def public_cover(url):
    parsed=urllib.parse.urlsplit(url)
    if parsed.scheme!='https' or parsed.hostname not in {'www.gutenberg.org','gutenberg.org'}:return None
    folder=Path.home()/'.cache/look/book-covers';folder.mkdir(parents=True,exist_ok=True)
    out=folder/(hashlib.sha256(url.encode()).hexdigest()+'.jpg')
    for suffix in ('.png','.jpg','.webp'):
        cached=out.with_suffix(suffix)
        if cached.is_file():return cached
    with gutenberg_open(url) as response:
        final=urllib.parse.urlsplit(response.url)
        if final.scheme!='https' or final.hostname not in {'www.gutenberg.org','gutenberg.org'}:return None
        if response.headers.get_content_type() not in {'image/jpeg','image/png','image/webp'}:return None
        data=response.read(MAX_COVER_BYTES+1)
        if len(data)>MAX_COVER_BYTES:return None
    # Keep a correct suffix: native terminals cannot infer PNG from a JPG name.
    suffix={'image/png':'.png','image/webp':'.webp'}.get(response.headers.get_content_type(),'.jpg')
    out=out.with_suffix(suffix)
    fd,temp=tempfile.mkstemp(dir=folder)
    try:
        with os.fdopen(fd,'wb') as stream:stream.write(data)
        os.replace(temp,out)
    finally:Path(temp).unlink(missing_ok=True)
    return out


class GutenbergRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self,req,fp,code,msg,headers,newurl):
        parsed=urllib.parse.urlsplit(newurl)
        if parsed.scheme!='https' or parsed.hostname not in {'www.gutenberg.org','gutenberg.org'}:
            raise ValueError('Cover redirected outside Project Gutenberg')
        return super().redirect_request(req,fp,code,msg,headers,newurl)


def gutenberg_open(url):
    return urllib.request.build_opener(GutenbergRedirect()).open(url,timeout=8)


def catalog_cover(url):
    parsed=urllib.parse.urlsplit(url)
    if parsed.scheme!='https' or parsed.hostname not in {'www.gutenberg.org','gutenberg.org'} or not re.fullmatch(r'/ebooks/[0-9]+\.opds',parsed.path):return None
    root=Path.home()/'.cache/look/book-covers';root.mkdir(parents=True,exist_ok=True)
    token=hashlib.sha256(url.encode()).hexdigest();metadata=root/(token+'.json')
    import json,time
    try:
        saved=json.loads(metadata.read_text())
        if time.time()-saved['time']<86400:return public_cover(saved['url']) if saved['url'] else None
    except (OSError,ValueError,KeyError):pass
    with gutenberg_open(url) as response:entry=book_core.xml(response.read(book_core.MAX_METADATA_BYTES+1))
    image=next((n.get('href') for n in entry.iter() if n.tag.endswith('link') and n.get('rel')=='http://opds-spec.org/image' and n.get('href','').startswith('https://')),None)
    metadata.write_text(json.dumps({'url':image,'time':time.time()}))
    return public_cover(image) if image else None
