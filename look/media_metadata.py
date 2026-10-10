"""Owner-local metadata corrections beside media; audio bytes stay untouched."""
from __future__ import annotations
import json
import os
from pathlib import Path
import tempfile
import time
try: from . import media_core, media_sidecar
except ImportError: import media_core, media_sidecar

FIELDS=('artist','album_artist','album','title','track','disc')
EXPECTED=(*FIELDS,'bytes','mtime')
MAX_BATCH=1000


def changes(values):
    if not isinstance(values,dict) or not values or set(values)-set(FIELDS):raise ValueError('Choose artist, album_artist, album, title, track or disc')
    result={}
    for key,value in values.items():
        if key in {'track','disc'}:
            if isinstance(value,bool) or not isinstance(value,int) or not 1<=value<=999:raise ValueError(key+' must be 1–999')
        elif not isinstance(value,str) or not value.strip() or len(value)>300 or any(ord(c)<32 for c in value):raise ValueError(key+' must contain 1–300 printable characters')
        result[key]=value.strip() if isinstance(value,str) else value
    return result


def atomic(path,data):
    fd,temp=tempfile.mkstemp(prefix='.'+path.name,dir=path.parent)
    try:
        with os.fdopen(fd,'wb') as stream:stream.write(data);stream.flush();os.fsync(stream.fileno())
        os.replace(temp,path)
    finally:
        if os.path.exists(temp):os.unlink(temp)


def edit(library_path,payload):
    if not isinstance(payload,dict):raise ValueError('Metadata request must be an object')
    values=changes(payload.get('changes'));items=payload.get('entries')
    if not isinstance(items,list) or not 1<=len(items)<=MAX_BATCH:raise ValueError('Select 1–1,000 tracks per node')
    if any(not isinstance(item,dict) or not isinstance(item.get('id'),str) or not isinstance(item.get('expected'),dict) or set(item['expected'])!=set(EXPECTED) for item in items):raise ValueError('Each track requires its catalog ID and expected metadata')
    if len({item['id'] for item in items})!=len(items):raise ValueError('Duplicate track selection')
    library_path=Path(library_path)
    with media_core.library_lock(library_path):
        library=media_core.normalize_library(json.loads(library_path.read_text()))
        indexed={row['id']:row for row in library['entries']};prepared={};updated=[]
        for item in items:
            row=indexed.get(item['id'])
            if not row:raise ValueError('Track is no longer in this node’s catalog; refresh first')
            if {key:row.get(key) for key in EXPECTED}!=item['expected']:raise ValueError('Metadata changed since selection; refresh before editing')
            path=Path(row['path']);stat=path.stat()
            if not path.is_file() or stat.st_size!=row['bytes'] or stat.st_mtime!=row['mtime']:raise ValueError('Media file changed; rescan before editing')
            sidecar=path.with_suffix('.info.json')
            if sidecar.is_symlink():raise ValueError('Metadata sidecar is a symlink')
            original=sidecar.read_bytes() if sidecar.exists() else None
            if original is not None and len(original)>4*1024*1024:raise ValueError('Metadata sidecar is too large')
            data=json.loads(original) if original is not None else {}
            if not isinstance(data,dict):raise ValueError('Metadata sidecar must be an object')
            current=media_sidecar.load(path)
            if any(current.get(key) and current[key]!=row.get(key) for key in FIELDS):raise ValueError('Metadata sidecar changed; rescan before editing')
            applied=dict(values)
            if 'artist' in applied and 'album_artist' not in applied and row.get('album_artist') in {None,'',row.get('artist')}:
                applied['album_artist']=applied['artist']
            data.update(applied);replacement=(json.dumps(data,ensure_ascii=False,indent=2)+'\n').encode()
            if sidecar in prepared and prepared[sidecar][1]!=replacement:raise ValueError('Selected files share conflicting metadata sidecars')
            prepared[sidecar]=(original,replacement)
            row.update(applied);updated.append(dict(row))
        written=[]
        try:
            for path,(_,replacement) in prepared.items():atomic(path,replacement);written.append(path)
            library['updated']=time.time();library['entries'].sort(key=media_core.entry_sort_key)
            atomic(library_path,(json.dumps(library,ensure_ascii=False,indent=2)+'\n').encode())
        except BaseException:
            for path in reversed(written):
                original,_=prepared[path]
                if original is None:path.unlink(missing_ok=True)
                else:atomic(path,original)
            raise
    return {'ok':True,'count':len(updated),'entries':updated,'storage':'metadata sidecars'}
