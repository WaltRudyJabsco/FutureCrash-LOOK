"""Offline notebook records and immutable revisions; no network or UI dependencies."""
from __future__ import annotations

import contextlib
import datetime as dt
import fcntl
import hashlib
import json
import math
import os
from pathlib import Path
import re
import tempfile
import time
import uuid

MAX_BODY = 256_000
MAX_REVISIONS = 20_000
SYNC_BATCH = 128
SYNC_BYTES = 4 * 1024 * 1024  # Leave room for the inventory inside ingress's 8 MiB limit.
KINDS = {'note', 'task', 'reminder'}
ID_PATTERN = re.compile(r'^[a-f0-9]{32}$')


def sync_batch(rows):
    result=[]; size=0
    for row in rows:
        encoded=len(json.dumps(row).encode('utf-8'))
        if result and (len(result)>=SYNC_BATCH or size+encoded>SYNC_BYTES): break
        result.append(row); size+=encoded
    return result


def atomic(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile('w', dir=path.parent, delete=False, encoding='utf-8') as out:
        temporary = Path(out.name)
        try:
            out.write(text)
            out.flush()
            os.fsync(out.fileno())
        except BaseException:
            temporary.unlink(missing_ok=True)
            raise
    try:
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


def timestamp(value, now=None):
    """Resolve simple local dates; persist epoch seconds so nodes agree on due time."""
    if value in (None, ''):
        return None
    if isinstance(value, (int, float)):
        result = float(value)
        if isinstance(value, bool) or not math.isfinite(result) or not 0 < result < 32_503_680_000:
            raise ValueError('Date is outside the supported range')
        return result
    text = str(value).strip().lower()
    current = dt.datetime.fromtimestamp(time.time() if now is None else now)
    quantities={'one':1,'two':2,'three':3,'four':4,'five':5,'six':6,'seven':7,'eight':8,'nine':9,'ten':10,'eleven':11,'twelve':12,'fifteen':15,'twenty':20,'thirty':30,'forty':40,'fifty':50,'sixty':60,'a':1,'an':1}
    relative = re.fullmatch(r'(?:in )?(\d+|[a-z]+) (second|minute|hour|day|week)s?', text)
    if relative:
        count=int(relative[1]) if relative[1].isdigit() else quantities.get(relative[1])
        if count is None or count<=0: raise ValueError('Use a positive duration, e.g. ten minutes')
        return timestamp(current.timestamp()+count*{'second':1,'minute':60,'hour':3600,'day':86400,'week':604800}[relative[2]])
    words = text.split()
    if len(words)==3 and words[1]=='at': words.pop(1)
    clock_only=re.fullmatch(r'(\d{1,2})(?::(\d{2}))?(am|pm)',text) or re.fullmatch(r'(\d{1,2}):(\d{2})',text)
    if clock_only:
        hour=int(clock_only[1]); minute=int(clock_only[2] or 0)
        period=clock_only[3] if len(clock_only.groups())==3 else None
        if period:
            if not 1<=hour<=12: raise ValueError('Invalid clock hour')
            hour=hour%12+(12 if period=='pm' else 0)
        target=current.replace(hour=hour,minute=minute,second=0,microsecond=0)
        if target<=current: target+=dt.timedelta(days=1)
        return target.timestamp()
    days = ['monday','tuesday','wednesday','thursday','friday','saturday','sunday']
    if words and (words[0] in {'today','tomorrow'} or words[0] in days):
        offset = (0 if words[0]=='today' else 1) if words[0] not in days else (days.index(words[0])-current.weekday()) % 7
        if words[0] in days and offset==0: offset=7
        clock = words[1] if len(words)==2 else '09:00'
        if len(words)>2: raise ValueError('Use a date and time, e.g. Saturday 09:00')
        match = re.fullmatch(r'(\d{1,2})(?::(\d{2}))?(am|pm)?', clock)
        if not match: raise ValueError('Use a time such as 09:00 or 9am')
        hour, minute = int(match[1]), int(match[2] or 0)
        if match[3]:
            if not 1<=hour<=12: raise ValueError('Invalid clock hour')
            hour = hour % 12 + (12 if match[3]=='pm' else 0)
        return (current+dt.timedelta(days=offset)).replace(hour=hour,minute=minute,second=0,microsecond=0).timestamp()
    try:
        return dt.datetime.fromisoformat(text.replace('z','+00:00')).timestamp()
    except ValueError as exc:
        raise ValueError('Use tomorrow, Saturday 9am, in 10 minutes, or an ISO date/time') from exc


class Notebook:
    def __init__(self, root=None, origin=None):
        self.root = Path(root or Path.home()/'.local/share/look/notebook')
        self.origin = str(origin or os.uname().nodename)
        self.revisions = self.root/'revisions'
        self.notes = self.root/'notes'
        for folder in (self.root,self.revisions,self.notes):
            folder.mkdir(parents=True,exist_ok=True,mode=0o700)
        self.lock_path = self.root/'lock'

    @contextlib.contextmanager
    def locked(self):
        with self.lock_path.open('a') as lock:
            fcntl.flock(lock,fcntl.LOCK_EX)
            yield

    def _read(self):
        rows=[]
        for path in sorted(self.revisions.glob('*.json')):
            rows.append(json.loads(path.read_text()))
        if len(rows)>MAX_REVISIONS: raise ValueError('Notebook revision limit reached; export/archive before continuing')
        return rows

    @staticmethod
    def validate(row):
        if not isinstance(row,dict): raise ValueError('Revision must be an object')
        for key in ('id','note'):
            if not ID_PATTERN.fullmatch(str(row.get(key,''))): raise ValueError('Invalid notebook ID')
        parents=row.get('parents')
        if not isinstance(parents,list) or len(parents)>128 or any(not ID_PATTERN.fullmatch(str(x)) for x in parents):
            raise ValueError('Invalid revision parents')
        data=row.get('data')
        if not isinstance(data,dict) or data.get('kind') not in KINDS: raise ValueError('Invalid note kind')
        if data.get('status') not in {'open','done','deleted'}: raise ValueError('Invalid note status')
        for field,limit in [('title',300),('body',MAX_BODY),('project',200),('target',200)]:
            if not isinstance(data.get(field),str) or len(data[field])>limit: raise ValueError('Invalid '+field)
        for field in ('due','remind_at'):
            if data.get(field) is not None and not isinstance(data[field],(int,float)):
                raise ValueError('Invalid persisted '+field)
            timestamp(data.get(field))
        if not isinstance(row.get('origin'),str) or len(row['origin'])>200: raise ValueError('Invalid origin')
        if not isinstance(row.get('created'),(int,float)) or not math.isfinite(row['created']): raise ValueError('Invalid revision date')
        if len(json.dumps(row))>MAX_BODY*8: raise ValueError('Revision too large')
        return row

    @staticmethod
    def heads(revisions):
        parent_ids={parent for row in revisions for parent in row['parents']}
        groups={}
        for row in revisions:
            if row['id'] not in parent_ids: groups.setdefault(row['note'],[]).append(row)
        for values in groups.values(): values.sort(key=lambda row:(row['created'],row['id']))
        return groups

    @staticmethod
    def markdown(data):
        return '# '+data['title']+'\n\n'+data['body'].rstrip()+'\n'

    def _revision(self,note,data,parents):
        if len(self._read()) >= MAX_REVISIONS:
            raise ValueError('Notebook revision limit reached; export/archive before continuing')
        row={'id':uuid.uuid4().hex,'note':note,'parents':parents,'origin':self.origin,'created':time.time(),'data':data}
        self.validate(row)
        atomic(self.revisions/(row['id']+'.json'),json.dumps(row,ensure_ascii=False,indent=2)+'\n')
        return row

    def _project(self,rows):
        groups=self.heads(rows)
        wanted=set()
        for note,heads in groups.items():
            live=[row for row in heads if row['data']['status']!='deleted']
            for row in live:
                filename=note+('.'+row['id'] if len(heads)>1 else '')+'.md'
                wanted.add(filename)
                path=self.notes/filename
                text=self.markdown(row['data'])
                if not path.exists() or path.read_text()!=text: atomic(path,text)
        for path in self.notes.glob('*.md'):
            if path.name not in wanted: path.unlink()

    def _import_edits(self,rows):
        # Import text-editor changes before refreshing projections or merging peers.
        for note,heads in self.heads(rows).items():
            for row in heads:
                if row['data']['status']=='deleted': continue
                path=self.notes/(note+('.'+row['id'] if len(heads)>1 else '')+'.md')
                if not path.is_file(): continue  # Use explicit delete; missing files aren't tombstones.
                text=path.read_text()
                if len(text)>MAX_BODY: raise ValueError('Edited note exceeds size limit')
                if text==self.markdown(row['data']): continue
                first,_,body=text.partition('\n')
                data=dict(row['data'],title=first.removeprefix('# ').strip() or 'Untitled',body=body.lstrip('\n'))
                rows.append(self._revision(note,data,[row['id']]))
        return rows

    def snapshot(self):
        with self.locked():
            rows=self._import_edits(self._read()); self._project(rows)
            return rows

    def list(self,query='',kind=None,include_done=False,scope='all',sort='updated'):
        result=[]
        revisions=self.snapshot()
        created={}
        for revision in revisions:
            if not revision['parents']:
                note=revision['note']; created[note]=min(created.get(note,revision['created']),revision['created'])
        for revision in revisions:
            created.setdefault(revision['note'],revision['created'])
        for note,heads in self.heads(revisions).items():
            conflict=len(heads)>1
            for row in heads:
                data=row['data']
                if data['status']=='deleted' or (not include_done and data['status']=='done'): continue
                if kind=='reminder':
                    if data['kind']!='reminder' and not data['remind_at']: continue
                elif kind and data['kind']!=kind: continue
                searchable=data['title']+' '+data['project']
                if scope=='all': searchable+=' '+data['body']
                tokens=query.casefold().split(); folded=searchable.casefold()
                if not all((word[1:] not in folded if word.startswith('\\') and len(word)>1 else word in folded) for word in tokens): continue
                name=note+('.'+row['id'] if conflict else '')+'.md'
                result.append(dict(data,id=note,revision=row['id'],conflict=conflict,path=str(self.notes/name),created=created[note],updated=row['created']))
        keys={'updated':lambda row:(-row['updated'],row['id']),
              'created':lambda row:(-row['created'],row['id']),
              'title':lambda row:(row['title'].casefold(),row['id']),
              'project':lambda row:(row['project'].casefold(),row['title'].casefold(),row['id']),
              'due':lambda row:(row['remind_at'] or row['due'] or float('inf'),row['title'].casefold(),row['id']),
              'type':lambda row:(row['kind'],row['title'].casefold(),row['id'])}
        if sort not in keys: raise ValueError('Unknown notebook sort')
        return sorted(result,key=keys[sort])

    def create(self,text,kind='note',project='Inbox',due=None,remind_at=None,target='all'):
        text=str(text).strip()
        if not text: raise ValueError('Note text is empty')
        data={'title':text.splitlines()[0][:100],'body':text,'kind':kind,'project':project,
              'status':'open','due':timestamp(due),'remind_at':timestamp(remind_at),'target':target}
        with self.locked():
            rows=self._import_edits(self._read())
            row=self._revision(uuid.uuid4().hex,data,[]); rows.append(row); self._project(rows)
        return row

    def change(self,identifier,changes,expected=None,resolve=False):
        with self.locked():
            rows=self._import_edits(self._read()); groups=self.heads(rows)
            matches=[key for key in groups if key.startswith(str(identifier))]
            if len(matches)!=1: raise ValueError('Note ID is missing or ambiguous')
            note=matches[0]; heads=groups[note]
            if len(heads)>1 and not resolve: raise ValueError('Conflicting revisions: edit each branch or use resolve explicitly')
            if expected and expected not in {row['id'] for row in heads}: raise ValueError('Note changed; reload before applying this action')
            data=dict(heads[-1]['data']); data.update(changes)
            row=self._revision(note,data,[head['id'] for head in heads]); rows.append(row); self._project(rows)
            return row

    def exchange(self,incoming,have):
        if not isinstance(incoming,list) or len(incoming)>SYNC_BATCH: raise ValueError('Sync batch too large')
        if not isinstance(have,list) or len(have)>MAX_REVISIONS: raise ValueError('Invalid sync inventory')
        for row in incoming: self.validate(row)
        with self.locked():
            rows=self._import_edits(self._read()); known={row['id']:row for row in rows}
            if len(set(known)|{row['id'] for row in incoming})>MAX_REVISIONS: raise ValueError('Notebook revision limit reached')
            combined=dict(known)
            for row in incoming:
                if row['id'] in combined and combined[row['id']] != row:
                    raise ValueError('Revision identity collision')
                combined[row['id']]=row
            for row in combined.values():
                for parent in row['parents']:
                    if parent == row['id'] or (parent in combined and combined[parent]['note'] != row['note']):
                        raise ValueError('Invalid revision ancestry')
            for row in incoming:
                if row['id'] in known:
                    if known[row['id']]!=row: raise ValueError('Revision identity collision')
                    continue
                # IDs are immutable. Revisions may arrive before parents during batching.
                atomic(self.revisions/(row['id']+'.json'),json.dumps(row,ensure_ascii=False,indent=2)+'\n')
                known[row['id']]=row
            rows=list(known.values()); self._project(rows)
            wanted=set(have)
            return {'ok':True,'revisions':sync_batch(row for row in rows if row['id'] not in wanted), 'ids':list(known)}

    def pending(self,node,now=None):
        now=time.time() if now is None else now
        return [dict(row,event_id='reminder:'+row['id']+':'+str(row['remind_at'])) for row in self.list()
                if not row['conflict'] and row['remind_at'] and row['remind_at']<=now
                and ('all' in row['target'].split(',') or node in row['target'].split(','))]

    def delivered(self,event_id):
        return (self.root/'delivered'/hashlib.sha256(event_id.encode()).hexdigest()).exists()

    def mark_delivered(self,event_id):
        atomic(self.root/'delivered'/hashlib.sha256(event_id.encode()).hexdigest(),'delivered\n')
