"""Verified animation backup to the user's already-authorized FabBack repository."""
import fcntl
import json
import os
from pathlib import Path
import shutil
import tempfile
import time
try:from . import animation_library as library,recovery
except ImportError:import animation_library as library;import recovery

def run():
    home=Path.home();state=recovery.root(home)
    with (state/'animations-backup.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        repo=recovery.checked_repository(home)
        if repo is None:raise ValueError('Authorized FabBack drive is disconnected')
        catalog=library.snapshot();rows=[r for r in catalog['items'].values() if r.get('sha256')]
        if not rows:raise ValueError('No downloaded animations to back up yet')
        if shutil.disk_usage(repo).free<4*1024**3:raise ValueError('FabBack has less than 4 GiB free')
        # Stage hardlinks on the archive volume: no duplicate GIF payloads and
        # no moving-target catalog while the downloader continues adding files.
        staging=library.root()/'.backup-snapshot'
        if staging.exists():shutil.rmtree(staging)
        staging.mkdir(mode=0o700)
        try:
            raw=json.dumps(catalog).encode();(staging/'catalog.json').write_bytes(raw)
            for row in rows:
                source=library.image(row['id']);os.link(source,staging/source.name)
            output=recovery.restic(home,repo,'backup',str(staging),'--host',recovery.capsule_owner(home),'--tag','fabric-animations','--json')
            summary=[json.loads(line) for line in output.splitlines() if json.loads(line).get('message_type')=='summary'][-1]
            sample=rows[0];snapshot=summary['snapshot_id']
            with tempfile.TemporaryDirectory(prefix='animation-restore-') as folder:
                recovery.restic(home,repo,'restore',snapshot,'--target',folder,'--include',str(staging/'catalog.json'),'--include',str(staging/(sample['id']+'.gif')))
                restored=Path(folder)/str(staging).lstrip('/')
                if (restored/'catalog.json').read_bytes()!=raw:raise ValueError('Catalog restore mismatch')
                if recovery.digest(restored/(sample['id']+'.gif'))!=sample['sha256']:raise ValueError('GIF restore mismatch')
            receipt={'snapshot':snapshot,'works':len(rows),'bytes':sum(r['bytes'] for r in rows),'verified_at':time.time(),'restore_tested':'catalog and one original GIF','tag':'fabric-animations','source':str(library.root())}
            recovery.private_json(state/'last-animations-backup.json',receipt);return receipt
        finally:shutil.rmtree(staging)

if __name__=='__main__':print(json.dumps(run()))
