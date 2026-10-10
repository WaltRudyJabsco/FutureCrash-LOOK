"""Remember a library destination and deliver verified imports without deleting sources."""
from __future__ import annotations
import hashlib
import shutil
import json
import os
from pathlib import Path, PurePosixPath
import re
import subprocess
import sys
import threading
import time
try: from . import fabric_files, media_core, managed_folders
except ImportError: import fabric_files, media_core, managed_folders

DEFAULTS={'node':'local','root':'~/Media'}
CATEGORIES=('music','movies','tv','books')


def config_path():return Path.home()/'.config/look/media_storage.json'


def settings(values=None):
    try:data={**DEFAULTS,**json.loads(config_path().read_text())}
    except (OSError,ValueError,TypeError):data=dict(DEFAULTS)
    if values is not None:
        if not isinstance(values,dict) or set(values)-set(DEFAULTS):raise ValueError('Choose node or root')
        data.update(values)
    if not isinstance(data.get('node'),str) or not re.fullmatch(r'[A-Za-z0-9_.-]+',data['node']):raise ValueError('Invalid library node name')
    value=data.get('root')
    if not isinstance(value,str) or not value or len(value)>1024 or any(ord(c)<32 for c in value) or not (value.startswith('/') or value.startswith('~/')) or value.rstrip('/') in {'','~'}:raise ValueError('root must be a dedicated absolute or ~/ directory')
    if values is not None:
        config_path().parent.mkdir(parents=True,exist_ok=True);atomic(config_path(),data)
    return data


def destination(kind):
    config=settings();path=config['root']
    return str(Path(path)/('music' if kind=='cd' else 'movies')) if config['node']=='local' else '@'+config['node']+':'+path


def atomic(path,data):
    import tempfile
    fd,temp=tempfile.mkstemp(prefix='.'+path.name,dir=path.parent)
    try:
        with os.fdopen(fd,'w') as stream:json.dump(data,stream,ensure_ascii=False);stream.flush();os.fsync(stream.fileno())
        os.replace(temp,path)
    finally:
        if os.path.exists(temp):os.unlink(temp)


def sha(path):
    digest=hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda:stream.read(1024*1024),b''):digest.update(block)
    return digest.hexdigest()


def manifest(folder):
    result={}
    for path in sorted(folder.rglob('*')):
        if path.is_symlink() or not (path.is_file() or path.is_dir()):raise ValueError('Library delivery requires regular files and directories')
        if path.is_file():result[path.relative_to(folder).as_posix()]=sha(path)
    if not result or len(result)>1000:raise ValueError('Import must contain 1–1,000 files')
    return result


def owner_request(action,payload):
    if action=='settings':
        config_file=Path.home()/'.config/look/media_library.json'
        try:config=json.loads(config_file.read_text())
        except (OSError,ValueError):config={'root':'~/Media'}
        if payload:
            if not isinstance(payload,dict) or set(payload)!={'root'}:raise ValueError('Choose a library root')
            config=dict(payload)
        value=config.get('root')
        if not isinstance(value,str) or not (value.startswith('/') or value.startswith('~/')):raise ValueError('Library root must be an absolute or ~/ path')
        root=Path(value).expanduser().resolve()
        if root in {Path(root.anchor),Path.home().resolve()}:raise ValueError('Choose a dedicated media directory')
        for name in (*CATEGORIES,'inbox'):(root/name).mkdir(parents=True,exist_ok=True)
        if payload:config_file.parent.mkdir(parents=True,exist_ok=True);atomic(config_file,config)
        return {'ok':True,'settings':config,'root':str(root),'directories':{name:str(root/name) for name in (*CATEGORIES,'inbox')}}
    root=fabric_files.parse('@local:'+str(payload.get('destination') or ''))
    path=Path(root.path).expanduser().resolve()
    if path in {Path(path.anchor),Path.home().resolve()}:raise ValueError('Choose a dedicated media directory')
    folder=payload.get('folder');identifier=payload.get('id');category=payload.get('category')
    if not isinstance(folder,str) or not folder or len(folder)>255 or folder in {'.','..'} or '/' in folder or '\\' in folder:raise ValueError('Invalid import folder name')
    if category not in CATEGORIES or not re.fullmatch('[0-9a-f]{32}',str(identifier)):raise ValueError('Invalid category or delivery ID')
    inbox=path/'inbox';stage=inbox/('.look-delivery-'+identifier);target=path/category/folder
    if stage.is_symlink() or target.is_symlink():raise ValueError('Import destination is a symlink')
    if action=='prepare':
        for name in (*CATEGORIES,'inbox'):(path/name).mkdir(parents=True,exist_ok=True)
        return {'ok':True,'path':str(inbox),'exists':stage.exists() or target.exists(),'stage':stage.name}
    if action!='publish':raise ValueError('Use prepare or publish')
    expected=payload.get('manifest')
    if not isinstance(expected,dict) or not 1<=len(expected)<=1000:raise ValueError('A file checksum manifest is required')
    for name,digest in expected.items():
        parts=PurePosixPath(name)
        if parts.is_absolute() or '..' in parts.parts or str(parts)=='.' or not isinstance(digest,str) or not re.fullmatch('[0-9a-f]{64}',digest):raise ValueError('Invalid checksum manifest')
    source=target if target.exists() else stage
    if not source.is_dir() or manifest(source)!=expected:raise ValueError('Destination checksums differ; source copy retained')
    if source==stage:
        import fcntl
        with (inbox/'.publish.lock').open('a') as lock:
            fcntl.flock(lock,fcntl.LOCK_EX)
            target.mkdir();moved=[]
            try:
                for child in stage.iterdir():child.rename(target/child.name);moved.append(child.name)
                stage.rmdir()
            except BaseException:
                for name in reversed(moved):(target/name).rename(stage/name)
                target.rmdir();raise
    library=Path.home()/'.local/share/look/media_library.json'
    managed_folders.register(target)
    media_core.update_library(library,lambda current:media_core.scan_root(target,current))
    return {'ok':True,'path':str(target),'verified_files':len(expected),'cataloged':True}


def receipt_path(identifier):
    if not re.fullmatch('[0-9a-f]{32}',str(identifier)):raise ValueError('Invalid import ID')
    return Path.home()/'.local/share/look/imports/jobs'/(identifier+'.delivery.json')


def receipt(identifier):
    path=receipt_path(identifier)
    if not path.exists():return None
    row=json.loads(path.read_text())
    if row.get('state') in {'queued','running'} and row.get('pid'):
        try:os.kill(row['pid'],0)
        except ProcessLookupError:
            row.update(state='failed',error='Delivery worker stopped; source retained');atomic(path,row)
    return row


def start(identifier,source,dest,kind='cd'):
    if fabric_files.parse(dest) is None:raise ValueError('Use @node:/path or @node:~/path for library delivery')
    path=receipt_path(identifier);path.parent.mkdir(parents=True,exist_ok=True)
    # The import submit lock also protects a delivery from two simultaneous starts.
    import fcntl
    with (path.parent/'delivery.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX)
        previous=receipt(identifier)
        if previous and previous['state'] in {'queued','running'}:raise ValueError('Library delivery already running')
        row={'id':identifier,'source':str(source),'destination':dest,'category':'music' if kind=='cd' else 'movies','state':'queued','stage':'queued','created':time.time(),'source_retained':True}
        atomic(path,row)
        try:
            with path.with_suffix('.log').open('ab') as log:
                process=subprocess.Popen([sys.executable,str(Path(__file__).resolve()),'worker',identifier],stdin=subprocess.DEVNULL,stdout=log,stderr=log,start_new_session=True)
            row['pid']=process.pid;atomic(path,row);threading.Thread(target=process.wait,daemon=True).start()
        except OSError as exc:row.update(state='failed',error=str(exc));atomic(path,row);raise
    return row


def cancel(identifier):
    import signal
    row=receipt(identifier)
    if not row or row['state'] not in {'queued','running'}:return row
    pid=row.get('pid')
    if pid:
        command=subprocess.run(['ps','-p',str(pid),'-o','args='],capture_output=True,text=True,timeout=3).stdout.strip()
        if command:
            if str(Path(__file__).resolve()) not in command or not command.endswith('worker '+identifier) or os.getpgid(pid)!=pid:raise ValueError('Delivery worker identity changed; cancellation refused')
            try:os.killpg(pid,signal.SIGTERM)
            except ProcessLookupError:pass
    row.update(state='cancelled',stage='cancelled',finished=time.time(),source_retained=True)
    atomic(receipt_path(identifier),row);return row


def remote(action,dest,payload):
    exe=shutil.which('fcl-node') or str(Path.home()/'.local/bin/fcl-node')
    command=[exe,'media-store',action,json.dumps(dict(payload,destination=dest.path)),'--node',dest.node,'--json']
    result=subprocess.run(command,capture_output=True,text=True,timeout=600)
    if result.returncode:raise RuntimeError((result.stderr or result.stdout or 'Library node request failed').strip())
    data=json.loads(result.stdout)
    if not data.get('ok'):raise RuntimeError(data.get('error') or 'Library node rejected delivery')
    return data


def worker(identifier):
    import fcntl
    path=receipt_path(identifier)
    with (path.parent/'delivery.lock').open('a') as lock:fcntl.flock(lock,fcntl.LOCK_EX);row=json.loads(path.read_text())
    def save(**values):row.update(values,updated=time.time());atomic(path,row)
    try:
        source=Path(row['source']);dest=fabric_files.parse(row['destination'])
        save(state='running',stage='checksumming source');expected=manifest(source)
        data={'folder':source.name,'manifest':expected,'category':row['category'],'id':identifier}
        prepared=remote('prepare',dest,data)
        if not prepared['exists']:
            class Progress:
                def update(self,**values):save(stage=values.get('stage','uploading'),progress=values)
            save(stage='copying to library');fabric_files.copy([source],str(fabric_files.Destination(dest.node,prepared['path'])),Progress(),root_name=prepared['stage'])
        save(stage='verifying destination');result=remote('publish',dest,data)
        save(state='complete',stage='complete',output=result['path'],verified_files=result['verified_files'],finished=time.time())
    except Exception as exc:save(state='failed',stage='delivery failed',error=str(exc)[:1000],finished=time.time())


if __name__=='__main__':
    if len(sys.argv)==3 and sys.argv[1]=='worker':worker(sys.argv[2])
    else:raise SystemExit('Use lk media storage --help')
