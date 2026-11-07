"""Resumable original-GIF archive. Network work never runs on a paint thread."""
from pathlib import Path
import hashlib
import html
import json
import os
import re
import shutil
import threading
import time
import urllib.parse
import urllib.request

SOURCE='https://gypsyastronaut.tumblr.com'
MAX_FILE=64*1024*1024
MIN_FREE=2*1024**3
_lock=threading.Lock()
_worker=None
_stop=threading.Event()

def config():
    try:return json.loads((Path.home()/'.config/look/animations.json').read_text())
    except (OSError,ValueError):return {}

def root():
    return Path(config().get('root',str(Path.home()/'Media/animations/gypsyastronaut'))).expanduser()

def identity(value):
    if not re.fullmatch(r'[0-9]{1,24}-[0-9]{1,4}',str(value)):raise ValueError('Invalid animation identity')
    return str(value)

def write(path,value):
    tmp=path.with_suffix('.tmp');tmp.write_text(json.dumps(value));os.replace(tmp,path)

def snapshot():
    try:return json.loads((root()/'catalog.json').read_text())
    except (OSError,ValueError):return {'items':{},'state':'empty','source':SOURCE}

def image(ident):
    path=root()/(identity(ident)+'.gif')
    if path.is_symlink() or not path.is_file():raise ValueError('Animation is not downloaded')
    return path

def allowed(url,api=False):
    p=urllib.parse.urlsplit(url)
    host=p.hostname or ''
    return p.scheme=='https' and not p.username and not p.password and p.port in (None,443) and (host=='gypsyastronaut.tumblr.com' if api else host.endswith('.media.tumblr.com'))

class Redirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self,req,fp,code,msg,headers,newurl):
        if not allowed(newurl,req.full_url.startswith(SOURCE)):raise ValueError('Unexpected source redirect')
        return super().redirect_request(req,fp,code,msg,headers,newurl)

def fetch(url,api=False):
    if not allowed(url,api):raise ValueError('Unsupported source URL')
    req=urllib.request.Request(url,headers={'User-Agent':'LOOK-Personal-Animation-Archive/1.0'})
    with urllib.request.build_opener(Redirect()).open(req,timeout=45) as response:data=response.read(MAX_FILE+1)
    if len(data)>MAX_FILE:raise ValueError('Source file exceeds 64 MiB')
    return data

def posts(raw):
    text=raw.decode('utf-8');text=text[text.index('{'):].rstrip(';\n ')
    return json.loads(text)

def entries(post):
    if post.get('type')!='photo':return []
    photos=post.get('photos') or [post]
    result=[]
    for index,photo in enumerate(photos):
        url=photo.get('photo-url-1280') or photo.get('photo-url-500')
        if not url or not allowed(url):continue
        # Keep only the source's explicitly supplied GIF original, never invent
        # a higher-resolution URL or scrape the site's blocked HTML pages.
        if not urllib.parse.urlsplit(url).path.lower().endswith('.gif'):continue
        title=html.unescape(re.sub('<[^>]+>',' ',post.get('photo-caption','')))
        title=' '.join(title.split())[:300] or ', '.join(post.get('tags',[])[:4]) or 'Gypsy Astronaut'
        result.append({'id':identity(str(post['id'])+'-'+str(index)),'url':url,'title':title,'post':post.get('url',SOURCE),'tags':post.get('tags',[])})
    return result

def start():
    global _worker
    with _lock:
        if _worker and _worker.is_alive():return snapshot()
        folder=root()
        # A configured removable/internal mount must exist; never silently write
        # a missing mount's archive onto the system volume.
        required=config().get('require_mount')
        if required and not os.path.ismount(required):raise ValueError('Animation storage drive is not mounted')
        folder.mkdir(parents=True,exist_ok=True)
        _stop.clear();_worker=threading.Thread(target=archive,name='animation-archive',daemon=True);_worker.start()
    return snapshot()

def archive():
    state=snapshot();state.update(state='indexing',error=None,source=SOURCE)
    rows=state.setdefault('items',{})
    try:
        offset=0
        while not _stop.is_set():
            batch=posts(fetch(SOURCE+'/api/read/json?'+urllib.parse.urlencode({'num':50,'start':offset}),True))
            state['posts_total']=batch.get('posts-total',0)
            for post in batch.get('posts',[]):
                for row in entries(post):rows.setdefault(row['id'],row)
            offset+=len(batch.get('posts',[]));state['posts_scanned']=offset
            write(root()/'catalog.json',state)
            if not batch.get('posts') or offset>=state['posts_total']:break
            if _stop.wait(1):break
        state['state']='downloading';write(root()/'catalog.json',state)
        for row in rows.values():
            if _stop.is_set():break
            path=root()/(identity(row['id'])+'.gif')
            if row.get('sha256') and path.is_file():continue
            if shutil.disk_usage(root()).free<MIN_FREE:raise ValueError('Archive paused: less than 2 GiB free')
            try:
                data=fetch(row['url'])
                if data[:6] not in (b'GIF87a',b'GIF89a'):raise ValueError('Source did not return a GIF')
                tmp=path.with_suffix('.part');tmp.write_bytes(data);os.replace(tmp,path)
                row.update(sha256=hashlib.sha256(data).hexdigest(),bytes=len(data));row.pop('error',None)
            except Exception as exc:row['error']=str(exc)[:300]
            state['downloaded']=sum(bool(r.get('sha256')) for r in rows.values())
            write(root()/'catalog.json',state)
            if _stop.wait(1):break
        state['state']='paused' if _stop.is_set() else ('partial' if any(r.get('error') for r in rows.values()) else 'complete')
    except Exception as exc:state.update(state='paused',error=str(exc)[:500])
    write(root()/'catalog.json',state)

def change(payload):
    if payload=={'action':'start'}:return start()
    if payload=={'action':'cancel'}:_stop.set();return snapshot()
    raise ValueError('Use start or cancel')
