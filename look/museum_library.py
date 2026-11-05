"""Owner-scoped catalog snapshots and shared offline image lookup."""
import hashlib
import json
import os
from pathlib import Path
import re
import uuid


def folder(owner):return Path.home()/'.cache/look/museum'/hashlib.sha256(owner.encode()).hexdigest()[:16]
def valid(ident):
    if not re.fullmatch(r'(met|aic)-[1-9][0-9]{0,9}',str(ident)):raise ValueError('Invalid artwork identity')
def read(path):
    try:
        result=json.loads(path.read_text())
        return result if isinstance(result,dict) else {}
    except (OSError,ValueError):return {}
def atomic(path,data):
    path.parent.mkdir(parents=True,exist_ok=True)
    tmp=path.with_name('.'+path.name+'.'+uuid.uuid4().hex);tmp.write_bytes(data);os.replace(tmp,path)
def remember(owner,result):
    atomic(folder(owner)/'catalog.json',json.dumps(result,ensure_ascii=False).encode())
def image(owner,ident):
    valid(ident)
    home=Path.home();paths=[home/'.local/share/future-crash-look/museum/images'/(ident+'.jpg'),folder(owner)/(ident+'.jpg')]
    saver=home/'.cache/look/museum-saver'
    if read(saver/'catalog.json').get('owner')==owner:paths.append(saver/(ident+'.jpg'))
    return next((path for path in paths if path.is_file() and not path.is_symlink()),None)
def store_image(owner,ident,data):
    valid(ident)
    if len(data)>20*1024*1024 or not (data.startswith(b'\xff\xd8\xff') or data.startswith(b'\x89PNG\r\n\x1a\n')):raise ValueError('Invalid artwork image')
    path=folder(owner)/(ident+'.jpg');atomic(path,data);return path

def snapshot(owner,query='',result=None):
    offline=result is None
    if offline:
        result=read(folder(owner)/'catalog.json')
        if owner=='local':
            local=read(Path.home()/'.local/share/future-crash-look/museum.json')
            if local:result=dict(local,items=list(local.get('items',{}).values()))
        saver=read(Path.home()/'.cache/look/museum-saver/catalog.json')
        rows={row['id']:row for row in result.get('items',[])}
        if saver.get('owner')==owner:
            for row in saver.get('items',{}).values():rows.setdefault(row['id'],row)
        result=dict(result,items=list(rows.values()))
    rows=[]
    for original in result.get('items',[]):
        row=dict(original);row['available_offline']=image(owner,row['id']) is not None
        row['owner_downloaded']=row.get('downloaded',False)
        if offline:row['downloaded']=row['available_offline']
        if query.casefold() in ' '.join(str(row.get(k,'')) for k in ('title','artist','date','medium','culture','collection')).casefold():rows.append(row)
    return dict(result,items=rows,offline=offline,owner=owner,collections=result.get('collections',{}),offline_count=sum(r['available_offline'] for r in rows))

def view(rows,mode='library',collection=None,offline_only=False):
    return [r for r in rows if (bool(r.get('removal_due')) if mode=='review' else not r.get('removal_due')) and (mode!='favorites' or r.get('favorite')) and (mode!='collections' or collection and collection in r.get('collections',[])) and (not offline_only or r.get('available_offline'))]
