"""One in-flight UI task and one replaceable request; input never waits for I/O."""
import threading
import time


class LatestWork:
    def __init__(self):
        self.condition=threading.Condition()
        self.key=None;self.value=None;self.updated=0.0
        self.pending=None;self.running=False;self.closed=False
        self.version=0;self.seen=0;self.thread=None;self.generation=0

    def get(self,key,compute,default=None,ttl=.5):
        with self.condition:
            changed=key!=self.key
            if changed:
                self.key=key;self.value=default;self.updated=0.0;self.generation+=1
            if changed or (not self.running and self.pending is None and time.monotonic()-self.updated>=ttl):
                self.pending=(key,self.generation,compute)
                if self.thread is None:
                    self.thread=threading.Thread(target=self._run,daemon=True,name='look-media-ui')
                    self.thread.start()
                self.condition.notify()
            return self.value

    def changed(self):
        with self.condition:
            changed=self.seen!=self.version;self.seen=self.version
            return changed

    def _run(self):
        while True:
            with self.condition:
                self.condition.wait_for(lambda:self.pending is not None or self.closed)
                if self.closed:return
                key,generation,compute=self.pending;self.pending=None;self.running=True
            try:value=compute()
            except Exception:value=None
            with self.condition:
                self.running=False
                if not self.closed and key==self.key and generation==self.generation:
                    if value!=self.value:self.version+=1
                    self.value=value;self.updated=time.monotonic()

    def close(self):
        with self.condition:
            self.closed=True;self.pending=None;self.condition.notify()


class MediaAction:
    """One explicit playback mutation in a child process; UI polling never blocks.

    File-backed output avoids both pipe deadlocks and process-wide stdout redirects
    while the parent continues rendering. Closing the desk leaves requested playback
    running, just as closing the small player does.
    """
    def __init__(self):
        self.process=None
        self.output=None

    @property
    def busy(self):
        return self.process is not None

    def start(self,argv,rows):
        import json
        import subprocess
        import tempfile
        if self.busy:return False
        self.output=tempfile.TemporaryFile(mode='w+b')
        try:
            with tempfile.TemporaryFile(mode='w+b') as source:
                source.write(json.dumps(rows).encode());source.seek(0)
                self.process=subprocess.Popen(argv,stdin=source,stdout=self.output,stderr=self.output)
        except Exception:
            self.output.close();self.output=None
            raise
        return True

    def poll(self):
        if self.process is None or self.process.poll() is None:return None
        code=self.process.returncode
        self.output.seek(0)
        message=self.output.read().decode('utf-8',errors='replace').strip()
        self.close()
        return code,message

    def close(self):
        if self.output is not None:self.output.close()
        self.output=None;self.process=None
