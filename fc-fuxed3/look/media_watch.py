#!/usr/bin/env python3
"""LOOK removable-media watcher.

Discovers newly mounted user volumes and indexes media without copying bytes.
Existing explicit media roots take precedence, preventing duplicate catalog rows.
"""
from __future__ import annotations
import json, os, sys, time
from pathlib import Path

HERE=Path(__file__).resolve().parent
if str(HERE) not in sys.path: sys.path.insert(0,str(HERE))
import media_core

LIBRARY=Path.home()/'.local/share/look/media_library.json'
STATUS=Path.home()/'.local/share/look/media_watch.json'
INTERVAL=15.0


def load():
    try: return media_core.normalize_library(json.loads(LIBRARY.read_text(encoding='utf-8')))
    except (OSError,ValueError,TypeError): return media_core.empty_library()


def save(data):
    LIBRARY.parent.mkdir(parents=True,exist_ok=True)
    tmp=LIBRARY.with_suffix('.json.tmp')
    tmp.write_text(json.dumps(media_core.normalize_library(data),indent=2,sort_keys=True)+'\n',encoding='utf-8')
    os.chmod(tmp,0o600); tmp.replace(LIBRARY)


def candidates():
    roots=[]
    if sys.platform=='darwin':
        base=Path('/Volumes')
        if base.is_dir(): roots.extend(p for p in base.iterdir() if p.is_dir() and not p.name.startswith('.'))
    elif sys.platform.startswith('linux'):
        user=os.environ.get('USER') or Path.home().name
        for base in (Path('/run/media')/user,Path('/media')/user):
            if base.is_dir(): roots.extend(p for p in base.iterdir() if p.is_dir() and not p.name.startswith('.'))
    return sorted({p.resolve() for p in roots},key=lambda p:str(p).casefold())


def covered(volume:Path, roots:list[str]):
    prefix=str(volume)+os.sep
    # If the user already chose a root anywhere on this volume, respect it instead
    # of scanning the whole disk and duplicating those catalog entries.
    return any(r==str(volume) or str(r).startswith(prefix) for r in roots)


def write_status(**fields):
    STATUS.parent.mkdir(parents=True,exist_ok=True)
    current={}
    try: current=json.loads(STATUS.read_text(encoding='utf-8'))
    except (OSError,ValueError,TypeError): pass
    current.update(fields); current['updated']=time.time()
    tmp=STATUS.with_suffix('.json.tmp')
    tmp.write_text(json.dumps(current,indent=2,sort_keys=True)+'\n',encoding='utf-8')
    os.chmod(tmp,0o600); tmp.replace(STATUS)


def scan_new(seen:set[str]):
    lib=load(); changed=False
    for volume in candidates():
        key=str(volume)
        if key in seen: continue
        seen.add(key)
        if covered(volume,lib.get('roots') or []):
            count=sum(1 for row in lib.get('entries') or [] if str(row.get('root') or '').startswith(key))
            write_status(state='indexed',volume=key,count=count,message='covered by explicit media root')
            continue
        try:
            write_status(state='scanning',volume=key,count=0,message='discovering removable media')
            before=len(lib.get('entries') or [])
            lib=media_core.scan_root(volume,lib); changed=True
            count=sum(1 for row in lib.get('entries') or [] if row.get('root')==key)
            write_status(state='indexed',volume=key,count=count,added=max(0,len(lib.get('entries') or [])-before),message='removable media ready')
        except (OSError,NotADirectoryError) as exc:
            write_status(state='error',volume=key,count=0,message=str(exc))
            continue
    if changed: save(lib)
    return seen


def main():
    seen=set(); write_status(state='watching',volume='',count=0,message='waiting for removable media')
    while True:
        live={str(p) for p in candidates()}
        seen.intersection_update(live)
        scan_new(seen)
        time.sleep(INTERVAL)

if __name__=='__main__':
    raise SystemExit(main())
