"""Optional background album covers; audio, tags and user artwork stay untouched."""
from __future__ import annotations
import fcntl
import hashlib
import json
import os
from pathlib import Path
import queue
import re
import tempfile
import threading
import time
import unicodedata
import urllib.parse
import urllib.request
import uuid

MAX_IMAGE_BYTES=2*1024*1024
MAX_METADATA_BYTES=512*1024
MISS_SECONDS=6*60*60
ERROR_SECONDS=5*60
RATE_SECONDS=1.1
USER_AGENT='FutureCrash-LOOK/8.16.1 (https://github.com/WaltRudyJabsco/FutureCrash-LOOK)'
_AUDIO={'.mp3','.m4a','.flac','.ogg','.opus','.wav','.aif','.aiff','.alac','.aac'}
_JOBS=queue.Queue(maxsize=64)
_LOCK=threading.Lock()
_PENDING=set()
_WORKER=None


def root():return Path.home()/'.cache/look/album-covers'



def enabled():
    value=os.environ.get('LOOK_MEDIA_ARTWORK_LOOKUP')
    if value is not None:return value=='1'
    try:
        data=json.loads((Path.home()/'.config/look/media_artwork.json').read_text())
        return isinstance(data,dict) and data.get('enabled') is True
    except (OSError,ValueError):return False


def configure(value):
    path=Path.home()/'.config/look/media_artwork.json'
    atomic(path,json.dumps({'enabled':bool(value)}).encode())
    return path

def normalized(value):
    text=unicodedata.normalize('NFKD',str(value or '')).casefold()
    return ' '.join(''.join(c if c.isalnum() or c.isspace() else ' ' for c in text if not unicodedata.combining(c)).split())


def album_key(row):
    artist=str(row.get('album_artist') or row.get('artist') or '').strip()
    album=str(row.get('album') or '').strip()
    if normalized(artist) in {'','unknown','unknown artist'} or normalized(album) in {'','unknown','unknown album','music','downloads'}:return None
    token=hashlib.sha256((normalized(artist)+'\0'+normalized(album)).encode()).hexdigest()[:32]
    return token,artist,album


def atomic(path,data):
    path.parent.mkdir(parents=True,exist_ok=True)
    fd,name=tempfile.mkstemp(prefix='.'+path.name,dir=path.parent)
    try:
        with os.fdopen(fd,'wb') as stream:stream.write(data)
        os.replace(name,path)
    finally:Path(name).unlink(missing_ok=True)


def record(token):
    try:
        data=json.loads((root()/(token+'.json')).read_text())
        return data if isinstance(data,dict) else {}
    except (OSError,ValueError):return {}



def retry_after(token):
    value=record(token).get('retry_at')
    return float(value) if isinstance(value,(int,float)) else 0

def cached(token):
    data=record(token);name=str(data.get('file') or '')
    if name and Path(name).name==name:
        path=root()/name
        if path.is_file():return path
    return None


def request(path,row=None):
    """Return a cached image or enqueue one lookup without waiting for the web."""
    path=Path(path)
    if path.suffix.casefold() not in _AUDIO or not path.is_file():return None
    if row is None:
        try:from . import media_core
        except ImportError:import media_core
        try:row=media_core.entry_from_path(path,sidecar=path.with_suffix('.info.json').is_file())
        except OSError:return None
    key=album_key(row)
    if key is None:return None
    token,artist,album=key
    art=cached(token)
    if art:return art
    if not enabled():return None
    if retry_after(token)>time.time():return None
    global _WORKER
    with _LOCK:
        if token in _PENDING:return None
        try:_JOBS.put_nowait((token,artist,album))
        except queue.Full:return None
        _PENDING.add(token)
        if _WORKER is None or not _WORKER.is_alive():
            _WORKER=threading.Thread(target=worker,name='album-cover-lookup',daemon=True);_WORKER.start()
    return None


def read_url(url,limit):
    request=urllib.request.Request(url,headers={'User-Agent':USER_AGENT,'Accept':'application/json' if 'musicbrainz.org' in url else 'image/*'})
    with urllib.request.urlopen(request,timeout=10) as response:data=response.read(limit+1)
    if len(data)>limit:raise ValueError('Artwork response exceeds size limit')
    return data


def rate_limit():
    root().mkdir(parents=True,exist_ok=True)
    with (root()/'musicbrainz-rate.lock').open('a+') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX);lock.seek(0)
        try:last=float(lock.read() or 0)
        except ValueError:last=0
        delay=RATE_SECONDS-(time.time()-last)
        if delay>0:time.sleep(delay)
        lock.seek(0);lock.truncate();lock.write(str(time.time()));lock.flush()


def choose_group(data,artist,album):
    matches={}
    for item in data.get('release-groups',[]):
        credit=''.join(str(c.get('name') or (c.get('artist') or {}).get('name') or '')+str(c.get('joinphrase') or '') for c in item.get('artist-credit',[]) if isinstance(c,dict))
        if normalized(item.get('title'))!=normalized(album) or normalized(credit)!=normalized(artist):continue
        if int(item.get('score') or 0)<90:continue
        try:group=str(uuid.UUID(str(item.get('id'))))
        except ValueError:continue
        matches[group]=item
    if len(matches)>1:return None,'ambiguous'
    return (next(iter(matches)), 'matched') if matches else (None,'missing')


def lookup(token,artist,album):
    """One exact artist/album match; provider ambiguity never chooses a random cover."""
    root().mkdir(parents=True,exist_ok=True)
    # LOOK and the node may request the same album in different processes.
    with (root()/(token+'.lock')).open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX)
        if cached(token):return record(token)
        if retry_after(token)>time.time():return record(token)
        result={'artist':artist,'album':album,'checked_at':time.time()}
        try:
            rate_limit()
            quoted=lambda text:'"'+str(text).replace('\\','\\\\').replace('"','\\"')+'"'
            query='releasegroup:'+quoted(album)+' AND artist:'+quoted(artist)
            url='https://musicbrainz.org/ws/2/release-group/?'+urllib.parse.urlencode({'query':query,'fmt':'json','limit':10})
            group,state=choose_group(json.loads(read_url(url,MAX_METADATA_BYTES)),artist,album)
            result.update(state=state,retry_at=time.time()+MISS_SECONDS)
            if group:
                source='https://coverartarchive.org/release-group/'+group+'/front-500'
                data=read_url(source,MAX_IMAGE_BYTES)
                suffix='.jpg' if data.startswith(b'\xff\xd8\xff') else '.png' if data.startswith(b'\x89PNG\r\n\x1a\n') else '.webp' if data.startswith(b'RIFF') and data[8:12]==b'WEBP' else ''
                if not suffix:raise ValueError('Cover response is not JPEG, PNG or WebP')
                image=root()/(token+suffix);atomic(image,data)
                result.update(state='ready',file=image.name,source=source,release_group=group,retry_at=0)
        except (OSError,ValueError,TypeError) as exc:
            result.update(state='error',reason=str(exc)[:300],retry_at=time.time()+ERROR_SECONDS)
        atomic(root()/(token+'.json'),json.dumps(result,ensure_ascii=False).encode())
        return result


def worker():
    while True:
        token,artist,album=_JOBS.get()
        try:lookup(token,artist,album)
        except Exception:pass  # Artwork failures cannot take down playback/navigation.
        finally:
            with _LOCK:_PENDING.discard(token)
            _JOBS.task_done()
