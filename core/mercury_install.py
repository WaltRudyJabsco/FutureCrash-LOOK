"""Pinned Mercury companion updates through the existing paired-node boundary."""
from __future__ import annotations
import fcntl
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import platform
import plistlib
import re
import shutil
import signal
import subprocess
import sys
import tarfile
import tempfile
import time
import urllib.request
import uuid

REVISION='56e79394b7c7ba7de2134294f4c836e385c8be02'
ARCHIVE_SHA256='8736b13503fa48c5381255d16d1cdcb956f99a5edd73f9b07e3dcd911f044ec2'
VERSION='1.6.0'
PORT=8765
LABEL='com.mercury.writer'


def root():return Path.home()/'.local/share/future-crash-look/mercury-install'
def app_root():return Path.home()/('Applications/Mercury-Writer' if platform.system()=='Darwin' else '.local/share/mercury-writer')


def atomic(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    temp=path.with_name(path.name+'.tmp')
    temp.write_text(json.dumps(value,indent=2));os.replace(temp,path)


def status():
    try:return json.loads((root()/'status.json').read_text())
    except (OSError,ValueError):return {'state':'idle','target_version':VERSION}


def api(path,payload=None,timeout=3):
    body=None if payload is None else json.dumps(payload).encode()
    request=urllib.request.Request(f'http://127.0.0.1:{PORT}'+path,data=body,headers={'Content-Type':'application/json'})
    with urllib.request.urlopen(request,timeout=timeout) as response:return json.load(response)


def extract(archive,directory):
    with tarfile.open(archive,'r:gz') as source:
        members=source.getmembers()
        if sum(item.size for item in members)>32*1024*1024:raise ValueError('Mercury archive too large')
        for item in members:
            path=PurePosixPath(item.name)
            if path.is_absolute() or '..' in path.parts or not (item.isfile() or item.isdir()):raise ValueError('Unsafe Mercury archive entry')
        # Entries have already been restricted to regular files/directories;
        # this also works on Python versions predating tarfile's data filter.
        source.extractall(directory,members=members,filter='data')
    sources=[path for path in directory.iterdir() if path.is_dir()]
    if len(sources)!=1:raise ValueError('Mercury archive root is ambiguous')
    return sources[0]


def service(action):
    if platform.system()=='Darwin':
        domain=f'gui/{os.getuid()}'
        if action=='stop':command=['launchctl','bootout',domain+'/'+LABEL]
        else:
            plist=Path.home()/'Library/LaunchAgents'/f'{LABEL}.plist'
            subprocess.run(['launchctl','bootstrap',domain,str(plist)],capture_output=True,timeout=15)
            command=['launchctl','kickstart','-k',domain+'/'+LABEL]
    else:command=['systemctl','--user',action,'server-mercury.service']
    result=subprocess.run(command,capture_output=True,text=True,timeout=20)
    if action!='stop' and result.returncode:raise RuntimeError(result.stderr.strip() or 'Mercury service did not start')


def configure_service(app):
    if platform.system()=='Darwin':
        plist=Path.home()/'Library/LaunchAgents'/f'{LABEL}.plist';plist.parent.mkdir(parents=True,exist_ok=True)
        value={'Label':LABEL,'ProgramArguments':[sys.executable,str(app/'mercury_server.py')],
               'WorkingDirectory':str(app),'RunAtLoad':True,'KeepAlive':True,
               'StandardOutPath':str(root()/'server.log'),'StandardErrorPath':str(root()/'server.log'),
               'EnvironmentVariables':{'PATH':os.environ.get('PATH','/usr/local/bin:/usr/bin:/bin')}}
        plist.write_bytes(plistlib.dumps(value));return
    unit=Path.home()/'.config/systemd/user/server-mercury.service'
    unit.parent.mkdir(parents=True,exist_ok=True)
    if unit.exists():
        text=unit.read_text()
        if str(app/'mercury_server.py') not in text and '%h/.local/share/mercury-writer/mercury_server.py' not in text:
            raise ValueError('Existing Mercury service uses a different application; preserve it and inspect its configuration')
    else:
        unit.write_text('[Unit]\nDescription=Mercury Writer\n[Service]\nType=simple\nWorkingDirectory='+str(app)+'\nExecStart='+sys.executable+' '+str(app/'mercury_server.py')+'\nRestart=on-failure\n[Install]\nWantedBy=default.target\n')
    subprocess.run(['systemctl','--user','daemon-reload'],check=True,capture_output=True,timeout=15)


def stop_existing(app):
    service('stop')
    try:version=api('/api/version',timeout=1)
    except OSError:return
    if version.get('name')!='Mercury Writer':raise RuntimeError('Port 8765 belongs to another application')
    lsof=shutil.which('lsof')
    if not lsof:raise RuntimeError('Mercury is unmanaged; lsof is required to verify its process before restart')
    result=subprocess.run([lsof,'-nP','-t','-iTCP:'+str(PORT),'-sTCP:LISTEN'],capture_output=True,text=True,timeout=5)
    for value in set(result.stdout.split()):
        if not value.isdigit():continue
        pid=int(value)
        command=subprocess.run(['ps','-p',value,'-o','command='],capture_output=True,text=True,timeout=3).stdout
        cwd=subprocess.run([lsof,'-a','-p',value,'-d','cwd','-Fn'],capture_output=True,text=True,timeout=3).stdout
        if str(app/'mercury_server.py') not in command and not ('mercury_server.py' in command and 'n'+str(app)+'\n' in cwd):
            raise RuntimeError('Listening process is not proven to belong to this Mercury installation')
        os.kill(pid,signal.SIGTERM)
    deadline=time.monotonic()+8
    while time.monotonic()<deadline:
        try:api('/api/version',timeout=.3)
        except OSError:return
        time.sleep(.1)
    raise RuntimeError('Previous Mercury server did not retire; app data was not changed')


def schedule(confirm=False,enable_sync=False):
    root().mkdir(parents=True,exist_ok=True)
    with (root()/'schedule.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX)
        return _schedule(confirm,enable_sync)


def _schedule(confirm=False,enable_sync=False):
    if confirm is not True:raise PermissionError('Mercury installation requires explicit confirmation')
    old=status()
    if old.get('state') in {'staged','downloading','installing','verifying'}:
        try:os.kill(old['pid'],0);return old
        except (OSError,KeyError):pass
    folder=root()/(time.strftime('%Y%m%d-%H%M%S')+'-'+uuid.uuid4().hex[:8]);folder.mkdir(parents=True,exist_ok=True)
    runner=folder/'runner.py';shutil.copy2(__file__,runner)
    receipt={'state':'staged','version':VERSION,'revision':REVISION,'backup':str(folder/'previous-app'),'enable_sync':enable_sync is True,'created':time.time()}
    with (folder/'install.log').open('ab') as log:
        process=subprocess.Popen([sys.executable,str(runner),'--run',str(folder),str(int(enable_sync is True))],stdin=subprocess.DEVNULL,stdout=log,stderr=log,start_new_session=True)
    receipt['pid']=process.pid;atomic(root()/'status.json',receipt)
    (folder/'go').touch();return receipt


def run(folder,enable_sync):
    deadline=time.monotonic()+15
    while not (folder/'go').exists():
        if time.monotonic()>deadline:return
        time.sleep(.05)
    receipt=status();app=app_root();stopped=False;changed=False
    def phase(state,**fields):
        receipt.update(state=state,updated=time.time(),**fields);atomic(root()/'status.json',receipt)
    try:
        if sys.version_info<(3,12):raise RuntimeError('Mercury 1.6 needs Python 3.12 or later; existing Mercury was left unchanged')
        if app.is_symlink():raise ValueError('Mercury app is a symlink; preserve it and update its owning checkout explicitly')
        phase('downloading')
        archive=folder/'release.tar.gz'
        url='https://codeload.github.com/WaltRudyJabsco/MercuryWriter/tar.gz/'+REVISION
        with urllib.request.urlopen(url,timeout=40) as response,archive.open('wb') as output:
            while chunk:=response.read(1024*1024):
                output.write(chunk)
                if output.tell()>8*1024*1024:raise ValueError('Mercury download exceeds its bounded archive limit')
        if hashlib.sha256(archive.read_bytes()).hexdigest()!=ARCHIVE_SHA256:raise ValueError('Mercury archive checksum mismatch')
        unpacked=folder/'source';unpacked.mkdir();source=extract(archive,unpacked)
        phase('installing');stop_existing(app);stopped=True
        if app.exists():shutil.copytree(app,folder/'previous-app',symlinks=True,ignore=shutil.ignore_patterns('__pycache__','*.log'))
        changed=True
        subprocess.run([sys.executable,str(source/'install_core.py'),'--install-dir',str(app),'--bin-dir',str(Path.home()/'.local/bin')],check=True,timeout=90)
        configure_service(app);service('start');phase('verifying')
        deadline=time.monotonic()+35
        while time.monotonic()<deadline:
            try:
                version=api('/api/version',timeout=1)
                if version.get('version')==VERSION:break
            except OSError:pass
            time.sleep(.3)
        else:raise RuntimeError('Mercury did not report its new running version')
        if enable_sync:api('/api/sync/config',{'enabled':True},timeout=10)
        state=api('/api/sync/status',timeout=15)
        phase('healthy',running_version=VERSION,sync_enabled=state['enabled'],projects=len(state.get('offline',[])),offline_ready=sum(row['ready'] for row in state.get('offline',[])),conflicts=len(state.get('conflicts',[])))
    except Exception as error:
        recovery=[]
        if changed and (folder/'previous-app').is_dir():
            try:
                service('stop')
                # Restore code/state in place, keeping the failed upgrade for inspection.
                if app.exists():shutil.move(str(app),str(folder/'failed-app'))
                shutil.copytree(folder/'previous-app',app,symlinks=True)
            except Exception as failure:recovery.append(str(failure))
        if stopped:
            try:configure_service(app);service('start')
            except Exception as failure:recovery.append(str(failure))
        phase('failed',error=str(error),recovery_errors=recovery)


if __name__=='__main__' and len(sys.argv)==4 and sys.argv[1]=='--run':run(Path(sys.argv[2]),sys.argv[3]=='1')
