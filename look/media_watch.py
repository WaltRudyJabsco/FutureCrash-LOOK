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


def scan_new(seen:set[str]):
    lib=load(); changed=False
    for volume in candidates():
        key=str(volume)
        if key in seen: continue
        seen.add(key)
        if covered(volume,lib.get('roots') or []): continue
        try:
            lib=media_core.scan_root(volume,lib); changed=True
        except (OSError,NotADirectoryError):
            continue
    if changed: save(lib)
    return seen


def main():
    seen=set()
    while True:
        live={str(p) for p in candidates()}
        seen.intersection_update(live)
        scan_new(seen)
        time.sleep(INTERVAL)

if __name__=='__main__':
    raise SystemExit(main())
