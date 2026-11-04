"""Immutable, human-readable event cards; separate from diagnostic logs."""
import hashlib
import json
import os
from pathlib import Path
import re
import tempfile
import textwrap
import time
import uuid
from datetime import datetime,timezone

KINDS={'note','feature','command','queued','download','deployment'}

def root():return Path.home()/'.local/share/look/receipts/cards'
def clean(value,limit):
    value=re.sub(r'[\x00-\x08\x0b-\x1f\x7f-\x9f]','',str(value or ''))
    if len(value)>limit:raise ValueError('Receipt content is too long')
    return value.strip()
def get(ident):
    if not re.fullmatch('[a-f0-9]{32}',str(ident)):raise ValueError('Choose a receipt ID from lk receipts')
    return json.loads((root()/(ident+'.json')).read_text())
def create(title,body,kind='note',source='',event_key=''):
    if kind not in KINDS:raise ValueError('Unknown receipt kind')
    title=clean(title,160);body=clean(body,20000);source=clean(source,500)
    if not title or not body:raise ValueError('A receipt needs a title and body')
    ident=hashlib.sha256(clean(event_key,1000).encode()).hexdigest()[:32] if event_key else uuid.uuid4().hex
    row=dict(schema=1,id=ident,created=time.time(),kind=kind,title=title,body=body,source=source)
    folder=root();folder.mkdir(parents=True,exist_ok=True,mode=0o700)
    fd,name=tempfile.mkstemp(prefix='.',suffix='.tmp',dir=folder)
    try:
        with os.fdopen(fd,'w') as out:json.dump(row,out,ensure_ascii=False)
        try:os.link(name,folder/(ident+'.json'))
        except FileExistsError:return get(ident)
    finally:Path(name).unlink(missing_ok=True)
    return row

def listing(query='',limit=100):
    query=clean(query,500).casefold();rows=[]
    for path in root().glob('*.json'):
        try:
            row=json.loads(path.read_text())
            if not query or query in (row['title']+' '+row['body']).casefold():rows.append(row)
        except (OSError,ValueError,KeyError):continue
    return sorted(rows,key=lambda row:row['created'],reverse=True)[:limit]

def render(row,columns=32):
    if not 24<=columns<=80:raise ValueError('Receipt width must be 24–80 columns')
    lines=['LOOK / FABRIC'.center(columns),'RECEIPT · '+row['kind'].upper(),'-'*columns]
    lines+=textwrap.wrap(row['title'],columns)+['']
    for paragraph in row['body'].splitlines():
        lines+=textwrap.wrap(paragraph,columns,replace_whitespace=False) or ['']
    lines+=['-'*columns,datetime.fromtimestamp(row['created'],timezone.utc).strftime('%Y-%m-%d %H:%M UTC')]
    if row.get('source'):lines+=textwrap.wrap('Source: '+row['source'],columns)
    lines+=textwrap.wrap('ID: '+row['id'],columns)
    return '\n'.join(lines)+'\n'
