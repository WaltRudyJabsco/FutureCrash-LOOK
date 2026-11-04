"""Bounded, disposable saver cache; all Fabric I/O stays on a daemon worker."""
import hashlib
import fcntl
import uuid
import json
import os
from pathlib import Path
import re
import threading
import urllib.parse
import urllib.request

MAX_WORKS=64
MAX_BYTES=256*1024*1024
MAX_IMAGE_BYTES=20*1024*1024

def folder():return Path.home()/'.cache/look/museum-saver'

def store(row,data,owner):
    root=folder();root.mkdir(parents=True,exist_ok=True)
    with (root/"write.lock").open("a") as lock:
        fcntl.flock(lock,fcntl.LOCK_EX)
        return _store(row,data,owner)

def _store(row,data,owner):
    ident=row.get('id','')
    if not re.fullmatch(r'(met|aic)-[1-9][0-9]{0,9}',ident):raise ValueError('Invalid artwork identity')
    if len(data)>MAX_IMAGE_BYTES or hashlib.sha256(data).hexdigest()!=row.get('sha256'):raise ValueError('Artwork checksum mismatch')
    root=folder();root.mkdir(parents=True,exist_ok=True)
    path=root/'catalog.json'
    try:state=json.loads(path.read_text())
    except (OSError,ValueError):state={'items':{}}
    rows=state['items'];rows.pop(ident,None);rows[ident]=dict(row,bytes=len(data))
    temporary=root/(ident+'.'+uuid.uuid4().hex+'.tmp');temporary.write_bytes(data);os.replace(temporary,root/(ident+'.jpg'))
    removed=[]
    while len(rows)>MAX_WORKS or sum(r.get('bytes',0) for r in rows.values())>MAX_BYTES:
        oldest=next(iter(rows));rows.pop(oldest);removed.append(oldest)
    temporary=root/('catalog.'+uuid.uuid4().hex+'.tmp');temporary.write_text(json.dumps({'owner':owner,'items':rows}));os.replace(temporary,path)
    for old in removed:(root/(old+'.jpg')).unlink(missing_ok=True)


def start():
    stop=threading.Event()
    def run():
        from museum_desk import Client,preference,BASE
        owner=preference()
        if owner=='local':return
        client=Client(owner)
        while not stop.is_set():
            try:
                rows=[r for r in client.snapshot()['items'] if r.get('downloaded')]
                for index,row in enumerate(rows):
                    if stop.is_set():return
                    url=BASE+'/v1/museum/image?'+urllib.parse.urlencode({'target':owner,'id':row['id']})
                    cached=folder()/(row['id']+'.jpg')
                    data=cached.read_bytes() if cached.is_file() else None
                    if data is None or hashlib.sha256(data).hexdigest()!=row.get('sha256'):
                        with urllib.request.urlopen(url,timeout=15) as response:data=response.read(MAX_IMAGE_BYTES+1)
                    store(row,data,owner)
                    # Warm a small gallery promptly, then rotate through the full
                    # owner's collection without retaining an unbounded mirror.
                    if stop.wait(.2 if index<12 else 20):return
            except (OSError,ValueError,KeyError):pass
            if stop.wait(60):return
    threading.Thread(target=run,name='museum-saver-cache',daemon=True).start()
    return stop
