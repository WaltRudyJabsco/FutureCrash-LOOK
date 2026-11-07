"""Private session-scoped task state; never reconstruct authority from model prose."""
import contextlib
import fcntl
import hashlib
import json
import os
import time
from pathlib import Path

TASK_TTL_SECONDS=1800

def root():return Path.home()/'.local/share/look/tasks'

@contextlib.contextmanager
def session(key):
    if not isinstance(key,str) or not 1<=len(key)<=256:raise ValueError('Use a bounded session identity')
    folder=root();folder.mkdir(parents=True,exist_ok=True,mode=0o700)
    name=hashlib.sha256(key.encode()).hexdigest();path=folder/(name+'.json')
    fd=os.open(folder/(name+'.lock'),os.O_CREAT|os.O_RDWR,0o600)
    with os.fdopen(fd,'w') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX)
        try:
            value=json.loads(path.read_text())
            if time.time()-value.get('updated',0)>TASK_TTL_SECONDS:value={}
        except (OSError,ValueError,TypeError):value={}
        def save():
            value['updated']=time.time()
            temp=path.with_suffix('.tmp')
            out=os.open(temp,os.O_WRONLY|os.O_CREAT|os.O_TRUNC,0o600)
            with os.fdopen(out,'w') as stream:
                json.dump(value,stream);stream.flush();os.fsync(stream.fileno())
            os.replace(temp,path)
        try:yield value,save
        finally:save()
