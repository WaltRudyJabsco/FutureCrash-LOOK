"""Bounded, on-demand duration previews; never scan the library during browsing."""
from concurrent.futures import Future
import threading
import hashlib
import json
import math
import os
from pathlib import Path
import shutil
import subprocess
import tempfile

PROBE_TIMEOUT_SECONDS=6
MAX_CACHED_DURATIONS=4096


def seconds(value):
    try:
        result=float(value)
        return result if math.isfinite(result) and result>0 else None
    except (TypeError,ValueError):return None


class DurationPreview:
    def __init__(self,resolve,cache=None):
        self.resolve=resolve
        self.path=cache or Path.home()/'.cache/look/media-durations.json'
        try:
            data=json.loads(self.path.read_text())
            self.values={key:value for key,value in data.items() if seconds(value)} if isinstance(data,dict) else {}
        except (OSError,ValueError):self.values={}
        self.attempted=set();self.pending=None
        self.closed=False
        self.ffprobe=shutil.which('ffprobe')

    @staticmethod
    def key(row):
        fields=[(item.get('node'),item.get('id'),item.get('path'),item.get('bytes'),item.get('mtime'))
                for item in [row,*(row.get('sources') or row.get('locations') or [])] if isinstance(item,dict)]
        return hashlib.sha256(json.dumps(fields,sort_keys=True).encode()).hexdigest()

    def value(self,row):
        for item in [row,*(row.get('sources') or row.get('locations') or [])]:
            value=seconds(item.get('duration') or item.get('duration_seconds'))
            if value:return value
        return seconds(self.values.get(self.key(row)))

    def probe(self,row):
        source=self.resolve(row)
        result=subprocess.run([self.ffprobe,'-v','error','-analyzeduration','0','-probesize','65536',
            '-show_entries','format=duration','-of','default=noprint_wrappers=1:nokey=1',str(source)],
            capture_output=True,text=True,timeout=PROBE_TIMEOUT_SECONDS,check=True)
        return seconds(result.stdout.strip())

    def submit(self,row):
        future=Future()
        def run():
            if not future.set_running_or_notify_cancel():return
            try:future.set_result(self.probe(row))
            except Exception as exc:future.set_exception(exc)
        # Like artwork preparation, a bounded probe must never hold the UI open.
        threading.Thread(target=run,name='look-duration',daemon=True).start()
        return future

    def poll(self,rows):
        """Collect a completed probe, then request one currently visible unknown."""
        changed=False
        if self.pending and self.pending[1].done():
            key,future=self.pending;self.pending=None
            try:value=future.result()
            except Exception:value=None
            if value:
                self.values[key]=value;changed=True
                self.values=dict(list(self.values.items())[-MAX_CACHED_DURATIONS:])
                temporary=None
                try:
                    self.path.parent.mkdir(parents=True,exist_ok=True)
                    with tempfile.NamedTemporaryFile('w',dir=self.path.parent,delete=False) as stream:
                        json.dump(self.values,stream);temporary=stream.name
                    os.replace(temporary,self.path)
                except OSError:
                    if temporary:
                        try:os.unlink(temporary)
                        except OSError:pass
        if not self.closed and self.ffprobe and self.pending is None:
            for row in rows:
                key=self.key(row)
                if self.value(row) is not None or key in self.attempted:continue
                self.attempted.add(key);self.pending=(key,self.submit(dict(row)));break
        return changed

    def close(self):
        self.closed=True
        if self.pending:self.pending[1].cancel()
