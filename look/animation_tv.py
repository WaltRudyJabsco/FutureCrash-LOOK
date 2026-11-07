"""Shared offline animation cache, terminal visual, and native TV entry point."""
import argparse
import hashlib
import functools
import fcntl
import json
import os
from pathlib import Path
import random
import re
import subprocess
import sys
import threading
import time
import urllib.parse
import urllib.request

MAX_FILE=64*1024*1024
MAX_CACHE=512*1024*1024
MAX_ITEMS=128
INTERVAL=30
_RUN_SEED=random.SystemRandom().randrange(2**63)
_cache_lock=threading.Lock()
_rows=[]
_checked=0

def config():
    try:return json.loads((Path.home()/'.config/look/animations.json').read_text())
    except (OSError,ValueError):return {}

def cache():return Path.home()/'.cache/look/gypsy'

def request(path='',payload=None):
    query=urllib.parse.urlencode({'target':config().get('node','local')})
    url='http://127.0.0.1:7332/v1/gypsy'+path+('&' if '?' in path else '?')+query
    req=urllib.request.Request(url,data=None if payload is None else json.dumps(payload).encode(),headers={'Content-Type':'application/json'})
    with urllib.request.urlopen(req,timeout=45) as response:
        return response.read(MAX_FILE+1) if path.startswith('/image') else json.load(response)

def available():
    global _rows,_checked
    if time.monotonic()-_checked<2:return _rows
    _checked=time.monotonic();found={}
    folders=[cache()]
    if config().get('node','local')=='local':folders.insert(0,Path(config().get('root',str(Path.home()/'Media/animations/gypsyastronaut'))).expanduser())
    for folder in folders:
        try:
            for row in json.loads((folder/'catalog.json').read_text()).get('items',{}).values():
                ident=row.get('id','')
                if not re.fullmatch(r'[0-9]{1,24}-[0-9]{1,4}',ident):continue
                path=folder/(ident+'.gif')
                if row.get('sha256') and path.is_file() and not path.is_symlink():found.setdefault(ident,(row,path))
        except (OSError,ValueError):pass
    _rows=list(found.values());return _rows

@functools.lru_cache(maxsize=16)
def shuffled_ids(ids,seed):
    return sorted(ids,key=lambda ident:hashlib.sha256((str(seed)+ident).encode()).digest())

def choose(elapsed,slot=0,displays=1,seed=None):
    if seed is None:seed=_RUN_SEED
    rows=available()
    if not rows:return None,None
    # A shuffled permutation plus disjoint display lanes guarantees different
    # images on attached monitors, including while individual lanes advance.
    mapping={row['id']:(row,path) for row,path in rows}
    order=[mapping[ident] for ident in shuffled_ids(tuple(mapping),seed)]
    lanes=min(max(1,displays),len(order));lane=order[slot%lanes::lanes]
    # Each display starts at its own phase and reshuffles its private lane on
    # every lap. Disjoint lanes still prevent simultaneous duplicate artwork.
    rng=random.Random(f'{seed}:display:{slot}')
    phase=rng.random()*INTERVAL
    step=int((elapsed+phase)//INTERVAL)+rng.randrange(len(lane))
    cycle,position=divmod(step,len(lane))
    lane_ids=tuple(row['id'] for row,path in lane)
    selected=shuffled_ids(lane_ids,f'{seed}:display:{slot}:lap:{cycle}')[position]
    return mapping[selected]

def store_cached(row,data):
    ident=row['id']
    if not re.fullmatch(r'[0-9]{1,24}-[0-9]{1,4}',ident):raise ValueError('Invalid animation identity')
    if len(data)>MAX_FILE or data[:6] not in (b'GIF87a',b'GIF89a') or hashlib.sha256(data).hexdigest()!=row['sha256']:raise ValueError('Animation checksum mismatch')
    folder=cache();folder.mkdir(parents=True,exist_ok=True)
    with (folder/'cache.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX)
        try:stored=json.loads((folder/'catalog.json').read_text()).get('items',{})
        except (OSError,ValueError):stored={}
        stored.pop(ident,None)
        while stored and (len(stored)>=MAX_ITEMS or sum(r.get('bytes',0) for r in stored.values())+len(data)>MAX_CACHE):
            oldest=next(iter(stored));stored.pop(oldest);(folder/(oldest+'.gif')).unlink(missing_ok=True)
        path=folder/(ident+'.gif');tmp=path.with_suffix('.part');tmp.write_bytes(data);os.replace(tmp,path)
        stored[ident]=dict(row,bytes=len(data));tmp=folder/'catalog.tmp';tmp.write_text(json.dumps({'items':stored}));os.replace(tmp,folder/'catalog.json')


def start():
    stop=threading.Event()
    def run():
        if config().get('node','local')=='local':return
        if not _cache_lock.acquire(blocking=False):return
        try:
            folder=cache();folder.mkdir(parents=True,exist_ok=True)
            while not stop.is_set():
                try:
                    rows=[r for r in request().get('items',{}).values() if r.get('sha256')]
                    random.shuffle(rows)
                    try:stored=json.loads((folder/'catalog.json').read_text()).get('items',{})
                    except (OSError,ValueError):stored={}
                    for row in rows[:MAX_ITEMS]:
                        if stop.is_set():return
                        ident=row['id']
                        if not re.fullmatch(r'[0-9]{1,24}-[0-9]{1,4}',ident):continue
                        path=folder/(ident+'.gif')
                        if ident in stored and path.is_file():continue
                        data=request('/image?id='+urllib.parse.quote(ident))
                        if len(data)>MAX_FILE or hashlib.sha256(data).hexdigest()!=row['sha256']:raise ValueError('Animation checksum mismatch')
                        store_cached(row,data);stored[ident]=row
                        if stop.wait(1):return
                except (OSError,ValueError,KeyError):pass
                if stop.wait(300):return
        finally:_cache_lock.release()
    threading.Thread(target=run,daemon=True,name='gypsy-cache').start();return stop

_term_stop=None

@functools.lru_cache(maxsize=32)
def _frame(width,height,phase):
    global _term_stop
    if _term_stop is None:_term_stop=start()
    row,path=choose(phase)
    if path:
        try:
            from PIL import Image
            with Image.open(path) as image:
                # Bounded lookup rather than decoding the complete animation.
                image.seek(int(phase*6)%min(120,getattr(image,'n_frames',1)))
                image=image.convert('L');image.thumbnail((width,max(1,(height-2)*2)))
                image=image.resize((image.width,max(1,image.height//2)))
                ramp=' .:-=+*#%@';pixels=list(image.getdata())
                lines=[''.join(ramp[v*9//255] for v in pixels[y*image.width:(y+1)*image.width]).center(width) for y in range(image.height)]
                lines+=[row['title']]
        except (ImportError,OSError,ValueError):lines=['Gypsy Astronaut','Use lk gypsy for original animated images.']
    else:lines=['Gypsy Astronaut','Preparing saved animations…','lk gypsy sync starts the archive on its owner.']
    return [re.sub(r'[\x00-\x1f\x7f-\x9f]',' ',line)[:width].ljust(width) for line in (lines+['']*height)[:height]]

def frame(width,height,phase):
    return _frame(width,height,int(phase*6)/6)

def main(argv=None):
    parser=argparse.ArgumentParser(prog='lk gypsy',description='Gypsy Astronaut TV · saved originals and offline cache')
    parser.add_argument('action',nargs='?',choices=['tv','status','sync','cancel'],default='tv')
    args=parser.parse_args(argv)
    try:
        if args.action!='tv':
            result=request(payload=None if args.action=='status' else {'action':'start' if args.action=='sync' else 'cancel'})
            print(json.dumps({k:v for k,v in result.items() if k!='items'},indent=2));print(str(sum(bool(r.get('sha256')) for r in result.get('items',{}).values()))+' saved animations');return 0
        import saver
        python=saver.interpreter()
        if python is None:raise ValueError('Run lk saver setup to install the graphics runtime')
        return subprocess.call([str(python),str(Path(__file__).with_name('animation_gui.py'))])
    except (OSError,ValueError,RuntimeError) as exc:print('Gypsy Astronaut · '+str(exc));return 1


def tools():
    return [{'type':'function','function':{'name':'animation_catalog','description':'List saved Gypsy Astronaut animations and archive status. Browser TV is /gypsy; native TV is lk gypsy. Does not start downloads or open windows.','parameters':{'type':'object','properties':{},'additionalProperties':False}}}]

def run_tool(args):
    if args:raise ValueError('No arguments expected')
    result=request();rows=[r for r in result.get('items',{}).values() if r.get('sha256')]
    return json.dumps({'state':result.get('state'),'saved':len(rows),'browser_path':'/gypsy','native_command':'lk gypsy','items':[{k:r.get(k) for k in ('id','title','post')} for r in rows[:20]]})
