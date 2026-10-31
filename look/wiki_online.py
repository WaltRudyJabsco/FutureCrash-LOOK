"""Explicit live English Wikipedia reads; fixed hosts, short waits and labelled cache."""
from pathlib import Path
import hashlib
import json
import time
import urllib.parse
import urllib.request
import urllib.error
import book_reader

HOST='https://en.wikipedia.org'
USER_AGENT='FutureCrash-LOOK/8.25.0 (https://github.com/WaltRudyJabsco/FutureCrash-LOOK)'
MAX_HTML_BYTES=4*1024*1024
MAX_IMAGE_BYTES=8*1024*1024
CACHE_SECONDS=900


def valid(url):
    parsed=urllib.parse.urlsplit(url)
    if parsed.scheme!='https' or parsed.hostname not in {'en.wikipedia.org','upload.wikimedia.org','thumb.wikimedia.org'} or parsed.username or parsed.port not in {None,443}:
        raise ValueError('Wikipedia requests must stay on the approved HTTPS hosts')
    return url


class Redirects(urllib.request.HTTPRedirectHandler):
    def redirect_request(self,req,fp,code,msg,headers,newurl):
        valid(newurl)
        return super().redirect_request(req,fp,code,msg,headers,newurl)


def read(url,limit):
    valid(url)
    request=urllib.request.Request(url,headers={'User-Agent':USER_AGENT})
    with urllib.request.build_opener(Redirects()).open(request,timeout=8) as response:
        data=response.read(limit+1)
        if len(data)>limit:raise ValueError('Wikipedia result exceeds the reader size limit')
        return data,response.headers.get_content_type()


def cached(kind,key,fetch):
    path=Path.home()/'.cache/look/wiki-live'/(hashlib.sha256((kind+'|'+key).encode()).hexdigest()+'.json')
    old=None
    try:old=json.loads(path.read_text())
    except (OSError,ValueError):pass
    if old and time.time()-old['fetched']<CACHE_SECONDS:
        return dict(old['value'],cached=True,fetched=old['fetched'])
    try:
        value=fetch();stamp=time.time()
        book_reader.write_json(path,{'value':value,'fetched':stamp})
        # This is a disposable browser cache, not a new article library.
        files=sorted(path.parent.glob('*.json'),key=lambda p:p.stat().st_mtime,reverse=True)
        for p in files[128:]:p.unlink(missing_ok=True)
        return dict(value,cached=False,fetched=stamp)
    except (OSError,ValueError) as exc:
        if old:return dict(old['value'],cached=True,stale=True,fetched=old['fetched'],warning='Live request unavailable; showing cached content')
        raise RuntimeError('Live Wikipedia unavailable; v selects the saved Fabric archive: '+str(exc)) from exc


def article(title=''):
    import wiki
    title=str(title or 'Main_Page').replace(' ','_')
    if len(title)>500:raise ValueError('Wikipedia title is too long')
    def fetch():
        url=HOST+'/w/rest.php/v1/page/'+urllib.parse.quote(title,safe='')+'/html'
        raw,ctype=read(url,MAX_HTML_BYTES)
        if ctype not in {'text/html','application/xhtml+xml'}:raise ValueError('Wikipedia did not return article HTML')
        value=wiki.article_payload(raw.decode('utf-8','replace'),title,title.replace('_',' '),wiki_host='en.wikipedia.org',live=True)
        value.update(source_url=HOST+'/wiki/'+urllib.parse.quote(title,safe=''),attribution='Wikipedia contributors · CC BY-SA 4.0')
        return value
    return cached('article-inline-v1',title,fetch)


def search(query):
    query=str(query).strip()
    if not query or len(query)>500:raise ValueError('Enter a Wikipedia search (up to 500 characters)')
    def fetch():
        url=HOST+'/w/rest.php/v1/search/page?'+urllib.parse.urlencode({'q':query,'limit':40})
        raw,ctype=read(url,2*1024*1024);value=json.loads(raw)
        return {'entries':[{'title':r['title'],'path':r['key']} for r in value.get('pages',[])][:40]}
    return cached('search',query,fetch)
