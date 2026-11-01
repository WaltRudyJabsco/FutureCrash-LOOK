#!/usr/bin/env python3
"""Install the pinned optional Mercury companion, or an explicitly selected checkout."""
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import subprocess
import sys
import tarfile
import tempfile
import urllib.request


def extract(archive, destination):
    with tarfile.open(archive,'r:gz') as source:
        members=source.getmembers()
        for item in members:
            path=PurePosixPath(item.name)
            if path.is_absolute() or '..' in path.parts or not (item.isfile() or item.isdir()):
                raise ValueError('Mercury archive contains an unsafe entry')
        source.extractall(destination, members=members, filter='data')
    roots=[path for path in destination.iterdir() if path.is_dir()]
    if len(roots)!=1:raise ValueError('Mercury archive must contain one source directory')
    return roots[0]


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source',type=Path)
    parser.add_argument('--dry-run',action='store_true')
    args=parser.parse_args()
    release=json.loads(Path(__file__).with_name('mercury.json').read_text())
    if args.dry_run:
        print('Mercury '+release['version']+' · install browser, CLI and local server; preserve existing manuscripts/config; sync remains a per-node choice')
        return
    with tempfile.TemporaryDirectory(prefix='fcl-mercury-') as stage:
        if args.source:
            source=args.source.expanduser().resolve()
        else:
            stage=Path(stage);archive=stage/'mercury.tar.gz'
            url='https://codeload.github.com/WaltRudyJabsco/MercuryWriter/tar.gz/'+release['revision']
            with urllib.request.urlopen(url,timeout=45) as response, archive.open('wb') as output:
                while chunk:=response.read(1024*1024):output.write(chunk)
            if hashlib.sha256(archive.read_bytes()).hexdigest()!=release['sha256']:
                raise ValueError('Mercury archive verification failed; nothing installed')
            unpacked=stage/'source';unpacked.mkdir();source=extract(archive,unpacked)
        script=source/'install_core.py'
        if not script.is_file():raise ValueError('Choose a Mercury 1.6+ source checkout with install_core.py')
        subprocess.run([sys.executable,str(script)],check=True)


if __name__=='__main__':main()
