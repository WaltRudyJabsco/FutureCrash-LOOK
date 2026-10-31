"""Book cover preparation for the existing asynchronous terminal preview renderer."""
from pathlib import Path
import os
import tempfile
import urllib.parse
import urllib.request
import book_cover
import media_art


def image(row):
    if row.get('cover_url'):return book_cover.public_cover(row['cover_url'])
    if row.get('url'):return book_cover.catalog_cover(row['url'])
    ident=str(row.get('id',''))
    if len(ident)!=64 or any(c not in '0123456789abcdef' for c in ident):return None
    if row.get('node','local')=='local':return book_cover.cover(row['path'],ident)
    folder=Path.home()/'.cache/look/book-covers';folder.mkdir(parents=True,exist_ok=True)
    for suffix in ('.png','.jpg','.webp'):
        cached=folder/(ident+suffix)
        if cached.is_file():return cached
    url='http://127.0.0.1:7332/v1/books/cover?'+urllib.parse.urlencode({'target':row['node'],'id':ident})
    with urllib.request.urlopen(url,timeout=12) as response:
        suffix={'image/png':'.png','image/jpeg':'.jpg','image/webp':'.webp'}.get(response.headers.get_content_type())
        if not suffix:return None
        data=response.read(book_cover.MAX_COVER_BYTES+1)
        if len(data)>book_cover.MAX_COVER_BYTES:return None
    out=folder/(ident+suffix);fd,temp=tempfile.mkstemp(dir=folder)
    try:
        with os.fdopen(fd,'wb') as stream:stream.write(data)
        os.replace(temp,out)
    finally:Path(temp).unlink(missing_ok=True)
    return out


def preview(row,width,height):
    path=image(row)
    return (media_art.symbol_lines(path,width,height),path) if path else ([],None)
