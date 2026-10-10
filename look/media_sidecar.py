"""Bounded import of yt-dlp descriptive sidecars; metadata never executes."""
from __future__ import annotations
import json
from pathlib import Path


def load(path):
    sidecar=Path(path).with_suffix('.info.json')
    try:
        if sidecar.stat().st_size>4*1024*1024: return {}
        data=json.loads(sidecar.read_text(encoding='utf-8'))
        if not isinstance(data,dict): return {}
        result={key:str(data[key])[:4000] for key in ('title','description','channel','uploader','webpage_url','artist','album','album_artist') if isinstance(data.get(key),str)}
        for key in ('track','disc'):
            try:
                value=int(data[key])
                if 0<value<1000:result[key]=value
            except (KeyError,TypeError,ValueError):pass
        result['tags']=[tag[:80] for tag in data.get('tags',[])[:32] if isinstance(tag,str)] if isinstance(data.get('tags'),list) else []
        return result if any(result.values()) else {}
    except (OSError,ValueError): return {}


def facts(data):
    return {'summary':' · '.join(value for value in (data.get('title'),data.get('description')) if value),
            'keywords':data.get('tags') or [],'source_url':data.get('webpage_url') or '', 'provenance':'source'}
