"""One authoritative listen-later queue per selected Fabric node."""
import json
import math
import os
from pathlib import Path
import threading
import time
import uuid
from urllib.parse import urlparse, parse_qs
try:
    from .downloads import youtube_url
except ImportError:
    from downloads import youtube_url

MAX_ITEMS = 500


def canonical_url(value):
    parsed = urlparse(youtube_url(value))
    parts = parsed.path.strip('/').split('/')
    video = parts[0] if parsed.hostname == 'youtu.be' else (
        parts[1] if len(parts) == 2 and parts[0] in {'shorts','live','embed'} else
        parse_qs(parsed.query).get('v',[''])[0])
    import re
    if not re.fullmatch(r'[A-Za-z0-9_-]{11}', video):
        raise ValueError('Paste one YouTube video link, not a channel or playlist')
    return 'https://www.youtube.com/watch?v=' + video


class Radio:
    def __init__(self, downloads, root=None):
        self.downloads = downloads
        self.root = Path(root or Path.home()/'.local/share/future-crash-look/radio')
        self.lock = threading.RLock()
        self.durations = {}

    def read(self):
        try:
            return json.loads((self.root/'queue.json').read_text())
        except FileNotFoundError:
            return {'items': [], 'revision': 0}

    def save(self, data):
        self.root.mkdir(parents=True, exist_ok=True)
        temporary = self.root/('.queue-' + uuid.uuid4().hex)
        with temporary.open('w') as stream:
            json.dump(data, stream)
        os.chmod(temporary, 0o600)
        os.replace(temporary, self.root/'queue.json')

    def duration(self, job):
        value = job.get('metadata', {}).get('duration')
        if value is not None:
            return value
        # Older receipts omitted duration, but retained the original sidecar.
        key = job['id']
        if key not in self.durations and job.get('stage') == 'complete':
            self.durations[key] = None
            folder = Path(job.get('directory', self.root/'audio')).resolve()
            for entry in job.get('files', []):
                path = Path(entry['path'])
                try:
                    if (path.name.endswith('.info.json') and not path.is_symlink()
                            and path.resolve().parent == folder
                            and folder.is_relative_to((self.root/'audio').resolve())
                            and path.stat().st_size <= 16*1024*1024):
                        self.durations[key] = json.loads(path.read_text()).get('duration')
                        break
                except (OSError, ValueError):
                    continue
        return self.durations.get(key)

    def snapshot(self):
        with self.lock:
            data = self.read()
            for item in data['items']:
                try:
                    job = self.downloads.get(item['job'])
                    item.update(stage=job['stage'], title=job.get('metadata',{}).get('title') or item['url'],
                                error=job.get('error',''), progress=job.get('progress',{}), duration=self.duration(job))
                except ValueError:
                    item.update(stage='failed', error='Download receipt missing')
            return data

    def change(self, data):
        with self.lock:
            state = self.read(); items = state['items']; action = data.get('action')
            if action == 'add':
                url = canonical_url(data.get('url',''))
                existing=next((i for i in items if i['url']==url),None)
                if existing:
                    return dict(self.snapshot(),radio_added={'id':existing['id'],'already_present':True})
                if len(items)>=MAX_ITEMS:raise ValueError('Radio queue is full')
                job = self.downloads.create(url, directory=str(self.root/'audio'), audio=True)
                items.append({'id':uuid.uuid4().hex,'url':url,'job':job['id'],
                              'position':0,'bookmark_revision':0,'done':False,'added':time.time()})
            else:
                item = next((i for i in items if i['id']==data.get('id')),None)
                if item is None:raise ValueError('Queue item no longer exists')
                if action == 'remove':
                    job=self.downloads.get(item['job'])
                    if job['stage'] not in {'complete','failed','cancelled','expired','publishing','indexing'}:
                        self.downloads.cancel(item['job'])
                    items.remove(item)
                elif action == 'move':
                    delta = data.get('delta')
                    if delta not in (-1,1):raise ValueError('Move must be -1 or 1')
                    index=items.index(item);items.pop(index);items.insert(max(0,min(len(items),index+delta)),item)
                elif action == 'progress':
                    position=float(data.get('position',0))
                    if not math.isfinite(position) or not 0<=position<=7*86400:raise ValueError('Invalid playback position')
                    if data.get('bookmark_revision')!=item['bookmark_revision']:
                        raise ValueError('Bookmark changed on another device; use lk ytr resolve NUMBER --keep local or --keep remote')
                    item.update(position=position,done=bool(data.get('done',False)),bookmark_revision=item['bookmark_revision']+1)
                elif action == 'retry':
                    job=self.downloads.get(item['job'])
                    if job['stage'] not in {'failed','cancelled','expired'}:raise ValueError('Download is not retryable')
                    item['job']=self.downloads.create(item['url'],directory=str(self.root/'audio'),audio=True)['id']
                else:raise ValueError('Unknown radio action')
            state['revision']+=1;self.save(state)
            result=self.snapshot()
            if action=='add':result['radio_added']={'id':items[-1]['id'],'already_present':False}
            return result

    def audio_file(self, item_id):
        with self.lock:
            item=next((i for i in self.read()['items'] if i['id']==item_id),None)
            if item is None:raise ValueError('Queue item not found')
            job=self.downloads.get(item['job'])
            if job['stage']!='complete' or not job.get('audio'):raise ValueError('Audio is not ready')
            path=Path(job['file']).resolve()
            if not path.is_relative_to((self.root/'audio').resolve()) or not path.is_file():raise ValueError('Audio cache unavailable')
            return path
