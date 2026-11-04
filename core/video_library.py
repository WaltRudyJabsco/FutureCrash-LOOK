"""Shared broad movie intent and compact human-video catalog for browser surfaces."""
import re
from pathlib import Path

EXTENSIONS={'.mp4','.m4v','.mov','.mkv','.webm','.avi','.wmv','.flv','.vob','.mts','.m2ts'}
MIN_VIDEO_BYTES=512*1024
MAX_RESULTS=1000


def intent(text):
    low=' '.join(str(text or '').casefold().strip(' .!?').split())
    low=re.sub(r'^(?:(?:can|could|would) you |please )','',low)
    low=re.sub(r'\s+please$','',low)
    noun=r'(?:movies?|films?|videos?)'
    library=r'(?:\s+(?:from|in|on)\s+(?:(?:our|my|the)\s+)?(?:fabric\s+)?library)?'
    if re.fullmatch(r'(?:play|put on)(?: (?:me|us))?(?: (?:a|an|any|some))?(?: (?:random|new))? '+noun+library,low) or low=='play something to watch':
        return {'action':'choose','recent':bool(re.search(r'\bnew\b',low))}
    if (re.fullmatch(r'(?:what|which) '+noun+r'(?: (?:are available(?: to (?:play|watch))?|do (?:we|i) have(?: available)?|can (?:we|i) (?:play|watch)))?'+library,low)
        or re.fullmatch(r'(?:show|list|browse)(?: me)?(?: (?:our|my|the|available))? '+noun+library,low)):
        return {'action':'list'}
    return None


def eligible(row):
    if not isinstance(row,dict) or row.get('fabric_hidden_by') or row.get('offline'):return False
    path=str(row.get('path') or '').replace('\\','/').casefold()
    if Path(path).suffix not in EXTENSIONS:return False
    if path.startswith(('/system/','/applications/','/usr/','/opt/','/library/')):return False
    if any(part in path for part in ('/applications/','/contents/','/application support/','/caches/','/cache/','/node_modules/','/site-packages/','/library/developer/','/library/frameworks/','/library/python/')):return False
    try:return int(row.get('bytes') or 0)>=MIN_VIDEO_BYTES
    except (TypeError,ValueError):return False


def catalog(data):
    seen=set();rows=[]
    fields=('id','node','path','title','name','media_type','bytes','digest','mtime','playability')
    for row in data.get('entries',[]):
        if not eligible(row):continue
        key=row.get('digest') or (Path(str(row.get('path') or '')).name.casefold(),row.get('bytes'))
        if key in seen:continue
        seen.add(key);rows.append({key:row[key] for key in fields if key in row})
    rows.sort(key=lambda row:str(row.get('title') or row.get('path') or '').casefold())
    return {'entries':rows[:MAX_RESULTS],'total':len(rows),'truncated':len(rows)>MAX_RESULTS}
