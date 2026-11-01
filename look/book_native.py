"""Explicit, checksum-pinned Bookokrat narration companion installation."""
from pathlib import Path
import hashlib
import io
import json
import os
import platform
import subprocess
import sys
import tarfile
import tempfile
import time
import urllib.request
import uuid

VERSION='0.3.14-look.1'
REPOSITORY='https://github.com/WaltRudyJabsco/Bookokrat-LOOK'
RELEASE='look-v'+VERSION
MAX_PACKAGE_BYTES=150*1024*1024
MAX_BINARY_BYTES=250*1024*1024
# Filled from the reviewed platform build receipts before release.
BUILDS={'aarch64-apple-darwin': {'commit': '497dfaff81a39b12f11030ea686ec52ac7aa3a75',
                          'sha256': '19f03d52881435b204e5b7322b21e222b3b869889ab7b69731c153b60ae5d79b'},
 'x86_64-unknown-linux-gnu': {'commit': '497dfaff81a39b12f11030ea686ec52ac7aa3a75',
                              'sha256': 'ea77d1e4e097021ff89733787a3448f7f8361506a7eeddec997bb37556e90c8b'}}


def target():
    system=platform.system().lower();machine=platform.machine().lower()
    return {('darwin','arm64'):'aarch64-apple-darwin',('linux','x86_64'):'x86_64-unknown-linux-gnu'}.get((system,machine))


def install_package(data,build,destination):
    if len(data)>MAX_PACKAGE_BYTES or hashlib.sha256(data).hexdigest()!=build['sha256']:
        raise ValueError('Native reader package verification failed')
    destination=Path(destination)
    if destination.exists():raise ValueError('A native reader already exists for this version; it was retained')
    destination.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.native-',dir=destination.parent) as temporary:
        stage=Path(temporary)/'package';stage.mkdir()
        with tarfile.open(fileobj=io.BytesIO(data),mode='r:gz') as archive:
            for name,limit in [('bookokrat',MAX_BINARY_BYTES),('LICENSE',1024*1024),('SOURCE.txt',1024*1024)]:
                member=archive.getmember(name)
                if not member.isfile() or member.size>limit:raise ValueError('Native reader package has an invalid member')
                source=archive.extractfile(member)
                with (stage/name).open('wb') as out:
                    while chunk:=source.read(1024*1024):out.write(chunk)
        os.chmod(stage/'bookokrat',0o755)
        result=subprocess.run([str(stage/'bookokrat'),'--version'],stdin=subprocess.DEVNULL,capture_output=True,text=True,timeout=10,check=True)
        if result.stdout.strip()!='bookokrat '+VERSION:raise ValueError('Native reader has an unexpected version')
        source=(stage/'SOURCE.txt').read_text().splitlines()
        if source!=[REPOSITORY,build['commit']]:raise ValueError('Native reader source reference differs from approved build')
        (stage/'install.json').write_text(json.dumps(dict(build,version=VERSION,binary_sha256=hashlib.sha256((stage/'bookokrat').read_bytes()).hexdigest()),indent=2)+'\n')
        os.replace(stage,destination)
    return destination


def install(confirmed=False):
    import fcntl
    import book_reader
    if confirmed is not True:raise PermissionError('Native reader installation requires confirmation')
    build=BUILDS.get(target())
    if not build:raise ValueError('No native companion build for this platform; the standard Bookokrat reader remains available')
    destination=Path.home()/'.local/share/look/book-reader-native'/VERSION
    if (destination/'bookokrat').is_file():
        receipt=json.loads((destination/'install.json').read_text())
        if receipt.get('commit')!=build['commit'] or receipt.get('binary_sha256')!=hashlib.sha256((destination/'bookokrat').read_bytes()).hexdigest():
            raise ValueError('The existing native companion differs from this approved build; it was retained')
        return book_reader.status()
    folder=book_reader.setup_root();folder.mkdir(parents=True,exist_ok=True)
    with (folder/'launch.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX)
        if book_reader.setup_state().get('state')=='installing':return book_reader.status()
        job=uuid.uuid4().hex
        book_reader.write_json(folder/'status.json',{'state':'installing','kind':'native','job':job,'created':time.time()})
        try:
            with (folder/'setup.log').open('ab') as log:
                subprocess.Popen([sys.executable,str(Path(__file__).resolve()),'--install-worker',job],stdin=subprocess.DEVNULL,stdout=log,stderr=log,start_new_session=True)
        except OSError as error:
            book_reader.write_json(folder/'status.json',{'state':'failed','job':job,'error':str(error)});raise
    return book_reader.status()


def worker(job):
    import book_reader
    folder=book_reader.setup_root();status=folder/'status.json'
    def update(**fields):
        value=json.loads(status.read_text())
        if value.get('job')!=job:raise RuntimeError('Native reader setup was superseded')
        book_reader.write_json(status,dict(value,**fields))
    try:
        update(pid=os.getpid());build=BUILDS[target()]
        asset='bookokrat-'+VERSION+'-'+target()+'.tar.gz'
        url=REPOSITORY+'/releases/download/'+RELEASE+'/'+asset
        request=urllib.request.Request(url,headers={'User-Agent':'LOOK-Books-Native-Setup'})
        with urllib.request.urlopen(request,timeout=90) as response:data=response.read(MAX_PACKAGE_BYTES+1)
        destination=Path.home()/'.local/share/look/book-reader-native'/VERSION
        install_package(data,build,destination)
        update(state='ready',finished=time.time())
    except Exception as error:update(state='failed',error=str(error),finished=time.time())


if __name__=='__main__' and len(sys.argv)==3 and sys.argv[1]=='--install-worker':worker(sys.argv[2])
