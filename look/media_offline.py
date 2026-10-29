"""Visible-row reachability and verified, explicit travel copies."""
from concurrent.futures import ThreadPoolExecutor
import hashlib
import os
from pathlib import Path
import shutil
import tempfile
import time
import urllib.parse
import urllib.request

PROBE_SECONDS = 1.0
RECHECK_SECONDS = 10.0
ROW_PROBE_SECONDS = 2.0
CHUNK_BYTES = 1024 * 1024


def locations(row):
    result=[];seen=set()
    for item in [row]+[x for x in row.get('locations',[]) if isinstance(x,dict)]:
        key=tuple(str(item.get(k) or '') for k in ('node','id','path'))
        if key not in seen:result.append(item);seen.add(key)
    return result


def download_url(source):
    return 'http://127.0.0.1:7332/v1/media/item?' + urllib.parse.urlencode({
        'node': source['node'], 'id': source['id'], 'path': source.get('path', ''),
        'representation': 'download'})


class Availability:
    """Probe only visible logical rows, with bounded concurrency and a short TTL."""
    def __init__(self, local_names):
        self.local_names = {str(x).casefold() for x in local_names}
        self.pool = ThreadPoolExecutor(max_workers=2, thread_name_prefix='media-available')
        self.pending = {}
        self.checked = {}

    def key(self, row):
        return tuple((str(x.get('node', '')), str(x.get('id', '')), str(x.get('path', '')))
                     for x in locations(row))

    def local(self, row):
        for x in locations(row):
            if str(x.get('node') or '').casefold() in self.local_names | {''}:
                if Path(str(x.get('path') or '')).expanduser().is_file():
                    return x
        return None

    def state(self, row):
        if self.local(row): return 'local'
        if str(row.get('path', '')).startswith(('http://', 'https://')): return 'stream'
        cached = self.checked.get(self.key(row))
        # Expiration schedules a background check; it must not brighten an
        # offline row until a successful probe actually changes its state.
        return cached[1] if cached else 'checking'

    def _probe(self, row):
        deadline=time.monotonic()+ROW_PROBE_SECONDS
        for x in locations(row):
            if time.monotonic()>=deadline:break
            if not x.get('node') or str(x['node']).casefold() in self.local_names or not x.get('id'):
                continue
            try:
                req = urllib.request.Request(download_url(x), method='HEAD')
                with urllib.request.urlopen(req, timeout=PROBE_SECONDS) as response:
                    if response.status < 400: return 'remote'
            except (OSError, ValueError): pass
        return 'offline'

    def poll(self, rows):
        changed = False
        for key, future in list(self.pending.items()):
            if future.done():
                try: state = future.result()
                except Exception: state = 'offline'
                self.checked[key] = (time.monotonic(), state)
                del self.pending[key]
                changed = True
        for row in rows:
            key = self.key(row)
            cached = self.checked.get(key)
            due = not cached or time.monotonic()-cached[0] >= RECHECK_SECONDS
            if self.state(row) not in {'local','stream'} and due and key not in self.pending and len(self.pending) < 2:
                self.pending[key] = self.pool.submit(self._probe, dict(row))
        return changed

    def close(self):
        self.pool.shutdown(wait=False, cancel_futures=True)


def keep(source, folder, *, progress=lambda done, total: None):
    """Publish only a complete, re-read-verified file; never overwrite another copy."""
    url = download_url(source)
    with urllib.request.urlopen(urllib.request.Request(url, method='HEAD'), timeout=PROBE_SECONDS*3) as response:
        total = int(response.headers.get('Content-Length') or 0)
    if total <= 0: raise ValueError('Source size unavailable; reconnect and refresh before copying')
    folder = Path(folder).expanduser()
    folder.mkdir(parents=True, exist_ok=True)
    if shutil.disk_usage(folder).free < total: raise ValueError('Not enough free space for this copy')
    name = Path(str(source.get('path') or 'media')).name
    token = hashlib.sha256(url.encode()).hexdigest()[:20]
    target_dir = folder / token
    target_dir.mkdir(exist_ok=True)
    target = target_dir / name
    expected = str(source.get('digest') or '').removeprefix('sha256:')
    def sha(path):
        with path.open('rb') as data: return hashlib.file_digest(data, 'sha256').hexdigest()
    if target.exists():
        if len(expected) == 64 and target.stat().st_size == total and sha(target) == expected:
            return target
        raise ValueError('A different copy already exists here; choose another destination')
    fd, temporary = tempfile.mkstemp(prefix='.offline-', dir=target_dir)
    stage = Path(temporary)
    try:
        copied = 0
        digest = hashlib.sha256()
        with os.fdopen(fd, 'wb') as output, urllib.request.urlopen(url, timeout=30) as response:
            if int(response.headers.get('Content-Length') or 0) != total:
                raise ValueError('Source changed; refresh and retry')
            while chunk := response.read(CHUNK_BYTES):
                copied += len(chunk)
                if copied > total: raise ValueError('Source length changed during transfer')
                output.write(chunk)
                digest.update(chunk)
                progress(copied, total)
            output.flush()
            os.fsync(output.fileno())
        if copied != total: raise ValueError('Incomplete transfer; reconnect and retry')
        if len(expected) == 64 and digest.hexdigest() != expected:
            raise ValueError('Source checksum mismatch; copy was not retained')
        if sha(stage) != digest.hexdigest(): raise ValueError('Local verification failed')
        # Atomic publication leaves no partial file for the local scanner/player.
        stage.replace(target)
        return target
    finally:
        stage.unlink(missing_ok=True)
