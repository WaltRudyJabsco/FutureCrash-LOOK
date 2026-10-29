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
