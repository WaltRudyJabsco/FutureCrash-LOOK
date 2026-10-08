"""Literal Fabric destinations and loopback file transport for LOOK."""
from __future__ import annotations
import json
import re
import shutil
import tarfile
import tempfile
import sys
import threading
import time
import uuid
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path

BASE = 'http://127.0.0.1:7332'


def literal(value):
    value = str(value).strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
        value = value[1:-1]
    return value.replace('\\ ', ' ')


@dataclass(frozen=True)
class Destination:
    node: str
    path: str

    def __str__(self):
        return f'@{self.node}:{self.path}'

    @property
    def name(self):
        return self.path.rstrip('/').rsplit('/', 1)[-1] or self.node

    @property
    def parent(self):
        if self.path == '/':
            return None
        return Destination(self.node, str(Path(self.path.rstrip('/')).parent))


def parse(value):
    raw = literal(value)
    if not raw.startswith('@'):
        return None
    match = re.fullmatch(r'@([^:/\s]+):(.*)', raw)
    if not match:
        raise ValueError('Use @node:/absolute/path or @node:~/path')
    node, path = match.groups()
    if not (path.startswith('/') or path == '~' or path.startswith('~/')):
        raise ValueError('Fabric paths must start with / or ~/ (the destination node home)')
    return Destination(node, path)


def request(route, params=None, data=None, length=None, timeout=None):
    url = BASE + route
    if params:
        url += '?' + urllib.parse.urlencode(params)
    headers = {} if length is None else {'Content-Length': str(length), 'Content-Type': 'application/x-tar'}
    req = urllib.request.Request(url, data=data, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=timeout if timeout is not None else (3600 if data is not None else 8)) as response:
            result = json.load(response)
    except urllib.error.HTTPError as exc:
        try: detail = json.load(exc).get('error', str(exc))
        except Exception: detail = str(exc)
        raise RuntimeError(detail) from exc
    if not result.get('ok', True):
        raise RuntimeError(result.get('error') or 'Fabric file operation failed')
    return result


def nodes():
    snapshot = request('/v1/nodes')
    names = set()
    local = (snapshot.get('self') or {}).get('name')
    if local: names.add(local)
    for peer in snapshot.get('peers') or []:
        if not peer.get('node') or not peer.get('trusted'): continue
        name = (peer['node'].get('identity') or {}).get('name') or peer.get('name')
        if name: names.add(name)
    return [Destination(name, '/') for name in sorted(names, key=str.casefold)]


def browse(dest,common=False):
    params={'target':dest.node,'path':dest.path}
    if common: params['mode']='common'
    return request('/v1/files/browse',params)


def copy(paths, destination, progress=None):
    dest = parse(destination)
    if dest is None: raise ValueError('Fabric destination required')
    paths = [Path(p).absolute() for p in paths]
    if len({p.name for p in paths}) != len(paths):
        raise ValueError('Selected sources have duplicate destination names')
    # A disk-backed archive bounds RAM and includes spaces verbatim, with no shell.
    started=time.monotonic()
    transfer=uuid.uuid4().hex
    with tempfile.TemporaryFile() as stream:
        class Writer:
            def write(self,data):
                written=stream.write(data)
                if progress: progress.update(stage='preparing',bytes=stream.tell(),total=0)
                return written
            def tell(self): return stream.tell()
        with tarfile.open(fileobj=Writer(), mode='w') as archive:
            def regular_only(info):
                if not (info.isfile() or info.isdir()):
                    raise ValueError(f'Fabric copy does not follow links or copy special files: {info.name}')
                return info
            for path in paths:
                archive.add(path, arcname=path.name, filter=regular_only)
        length = stream.tell(); stream.seek(0)
        if progress: progress.update(stage='connecting',bytes=0,total=length,transfer=transfer)
        result=request('/v1/files/copy', {'target': dest.node, 'path': dest.path, 'transfer': transfer}, stream, length)
        result['elapsed']=time.monotonic()-started
        if progress: progress.update(stage='complete',bytes=length,total=length)
        return result


def _size(count):
    count=float(count)
    for unit in ('B','KiB','MiB','GiB','TiB'):
        if count<1024 or unit=='TiB': return f'{count:.1f} {unit}'
        count/=1024


def progress_text(row,elapsed):
    stage=row.get('stage','preparing'); count=int(row.get('bytes') or 0); total=int(row.get('total') or 0)
    labels={'preparing':'preparing archive','connecting':'connecting to node','uploading':'uploading',
            'receiving':'receiving','confirming':'awaiting confirmation',
            'finalizing':'finalizing destination','complete':'copy confirmed','failed':'copy failed'}
    detail=f'{count/total*100:5.1f}% · {_size(count)} / {_size(total)}' if total else _size(count)
    speed=''
    if stage in {'uploading','receiving'} and count:
        duration=max(.01,time.monotonic()-row.get('upload_started',time.monotonic()-elapsed))
        speed=f' · {_size(count/duration)}/s'
    return f"COPY · {labels.get(stage,stage)} · {detail}{speed} · {elapsed:.1f}s"


class Progress:
    """One terminal owner: report preparation and poll gateway transfer stages."""
    def __init__(self):
        self.row={'stage':'preparing','bytes':0,'total':0}; self.lock=threading.Lock()
        self.stop=threading.Event(); self.started=time.monotonic(); self.worker=None

    def update(self,**fields):
        with self.lock: self.row.update(fields)

    def __enter__(self):
        if sys.stderr.isatty():
            self.worker=threading.Thread(target=self.run,daemon=True); self.worker.start()
        return self

    def run(self):
        next_poll=0
        while not self.stop.is_set():
            with self.lock: row=dict(self.row)
            if row.get('transfer') and row.get('stage') not in {'complete','failed'} and time.monotonic()>=next_poll:
                try:
                    status=request('/v1/files/copy/status',{'transfer':row['transfer']},timeout=1)
                    self.update(**status['transfer'])
                    with self.lock: row=dict(self.row)
                except Exception: pass
                next_poll=time.monotonic()+.5
            line=progress_text(row,time.monotonic()-self.started)
            width=max(1,shutil.get_terminal_size((100,24)).columns-1)
            sys.stderr.write('\r\033[2K'+(line if len(line)<=width else line[:max(0,width-1)]+'…'))
            sys.stderr.flush()
            self.stop.wait(.15)

    def __exit__(self,*args):
        self.stop.set()
        if self.worker:
            self.worker.join(timeout=2)
            sys.stderr.write('\r\033[2K'); sys.stderr.flush()
