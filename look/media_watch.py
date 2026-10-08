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
import managed_folders

LIBRARY=Path.home()/'.local/share/look/media_library.json'
STATUS=Path.home()/'.local/share/look/media_watch.json'
INTERVAL=15.0


def load():
    try: return media_core.normalize_library(json.loads(LIBRARY.read_text(encoding='utf-8')))
    except (OSError,ValueError,TypeError): return media_core.empty_library()


def save(data):
    # A mount scan contributes only its roots; retain concurrent download entries.
    roots=set(data.get('roots') or [])
    def merge(current):
        paths={row['path']:row for row in current['entries']}
        paths.update({row['path']:row for row in data.get('entries') or []})
        current['entries']=list(paths.values()); current['roots']=list(roots|set(current['roots']))
        return current
    media_core.update_library(LIBRARY,merge)


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


REFRESH_SECONDS=300.0


def refresh_existing(previous):
    """Inspect directory mtimes, refreshing changed folders without decoding media.

    Files rewritten in place without directory changes still require a manual
    rescan. Never automatically traverse an explicit whole-filesystem root.
    """
    import file_catalog
    library=load(); known={item['path']:item for item in library['entries']}
    by_folder={}
    for path,row in known.items(): by_folder.setdefault((row.get('root'),str(Path(path).parent)),[]).append(path)
    changes={}; removed=set(); current={}
    owned={str(path) for path in managed_folders.roots() if path.is_dir()}
    for root in sorted(set(library['roots'])|owned):
        base=Path(root).expanduser().resolve()
        if base==base.parent or not base.is_dir(): continue
        for folder,dirs,names in os.walk(base):
            dirs[:]=[name for name in dirs if not name.startswith('.')]
            try: stamp=Path(folder).stat().st_mtime_ns
            except OSError: continue
            key=(str(base),folder); current[key]=stamp
            if previous.get(key)==stamp: continue
            names=set(names)
            visible={str(Path(folder)/name) for name in names if not name.startswith('.') and Path(name).suffix.casefold() in media_core.MEDIA_EXTENSIONS}
            removed.update(path for path in by_folder.get(key,[]) if path not in visible)
            for path in visible:
                try:
                    row=media_core.entry_from_path(path,base,sidecar=Path(path).with_suffix('.info.json').name in names); old=known.get(path)
                    if old and old.get('bytes')==row['bytes'] and old.get('mtime')==row['mtime'] and old.get('source_url')==row.get('source_url') and old.get('description')==row.get('description'): continue
                    changes[path]=row
                    file_catalog.register(Path.home()/'.local/share/look/file_catalog.sqlite3',path)
                except (OSError,ValueError): continue
    # Deleted directories are removed only under a root we could inspect.
    live_roots={key[0] for key in current}
    for key in set(previous)-set(current):
        if key[0] in live_roots and not Path(key[1]).exists(): removed.update(by_folder.get(key,[]))
    if changes or removed:
        def merge(current_library):
            entries={item['path']:item for item in current_library['entries'] if item['path'] not in removed}
            entries.update(changes); current_library['entries']=list(entries.values())
            current_library['roots']=list(set(current_library['roots'])|owned)
            return current_library
        media_core.update_library(LIBRARY,merge)
        for path in removed: file_catalog.forget(Path.home()/'.local/share/look/file_catalog.sqlite3',path)
    managed_folders.refresh_catalog()
    write_status(refresh_seconds=REFRESH_SECONDS,last_refresh=time.time(),added_or_changed=len(changes),removed=len(removed),
                 refresh_message='existing scoped roots checked; whole-filesystem roots need manual rescan')
    return current


def main():
    seen=set(); previous={}; refreshed=0.0
    write_status(state='watching',volume='',count=0,message='waiting for removable media')
    while True:
        live={str(p) for p in candidates()}
        seen.intersection_update(live)
        scan_new(seen)
        if time.monotonic()-refreshed>=REFRESH_SECONDS:
            try: previous=refresh_existing(previous)
            except Exception as exc: write_status(refresh_error=str(exc))
            refreshed=time.monotonic()
        time.sleep(INTERVAL)

if __name__=='__main__':
    raise SystemExit(main())
