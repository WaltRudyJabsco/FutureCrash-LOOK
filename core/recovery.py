"""Essential Fabric recovery, with encrypted Restic storage and inert restores.

This is not a machine image. Models, media, installed code and generated indexes
are replaceable; identities, notebook revisions and personal state are not.
"""
from __future__ import annotations
import argparse
import contextlib
import fcntl
import hashlib
import json
import os
import re
from pathlib import Path, PurePosixPath
import secrets
import shutil
import socket
import sys
import tarfile
import sqlite3
import stat
import subprocess
import tempfile
import time

SCHEMA = 1
DAILY_SECONDS = 24 * 60 * 60
MIN_FREE_BYTES = 512 * 1024 * 1024
MAX_CAPSULE_BYTES = 512 * 1024 * 1024
CONFIG_TREES = ('.config/future-crash-look', '.config/look', '.future_crash')
STATE_TREES = ('.local/share/look/notebook', '.local/share/look/personalities',
               '.local/share/look/memory_queue', '.local/share/look/skill_feedback_queue',
               '.local/share/look/receipts', '.local/share/look/jobs', '.local/share/look/events',
               '.local/share/future-crash-look/artifacts',
               '.local/share/future-crash-look/albert-artifacts')
EXCLUDED = ['audio/video and documents referenced by catalogs', 'models and embeddings',
            'installed code (reinstall the recorded release)', 'generated file index',
            'logs, caches, sockets, PIDs, locks, transient playback',
            'SSH keys and operating-system accounts', 'other applications and their data']
SKIP_NAMES = {'recovery', 'recovery-keys', 'completions', 'advertisement.json', 'pair.json', 'lock'}
SKIP_SUFFIXES = ('.lock', '.log', '.pid', '.sock', '.tmp', '-wal', '-shm')


def root(home): return Path(home) / '.config/future-crash-look/recovery'
def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''): h.update(block)
    return h.hexdigest()


def private_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    fd, name = tempfile.mkstemp(dir=path.parent)
    try:
        with os.fdopen(fd, 'w') as out:
            json.dump(value, out, indent=2); out.write('\n')
        os.replace(name, path)
    finally:
        if os.path.exists(name): os.unlink(name)


def load_config(home):
    return json.loads((root(home) / 'destination.json').read_text())


def sources(home):
    """An explicit inventory: broad scans would accidentally back up media/code."""
    home = Path(home)
    candidates = []
    skipped = []
    for relative in CONFIG_TREES + STATE_TREES:
        base = home / relative
        if base.is_symlink():
            skipped.append(relative); continue
        if not base.exists(): continue
        for folder, dirs, files in os.walk(base, followlinks=False):
            for name in list(dirs):
                p = Path(folder) / name
                if p.is_symlink() or name in SKIP_NAMES:
                    dirs.remove(name); skipped.append(str(p.relative_to(home)))
            candidates.extend(Path(folder) / name for name in files)
    for relative in ('.local/share/look', '.local/share/future-crash-look'):
        base = home / relative
        if base.is_symlink():
            skipped.append(relative); continue
        if base.is_dir():
            candidates.extend(p for p in base.iterdir() if p.suffix in {'.json', '.sqlite3'}
                              and p.name not in {'file_catalog.sqlite3', 'media_session.json', 'install_manifest.json'})
    candidates += [home / '.future_crash_memory.json']
    candidates += [home / '.local/share/look' / name for name in
                   ('lo_access', 'lo_personality', 'lo_thinking', 'lo_think_display',
                    'ollama_model', 'skills.md', 'core.md')]
    candidates += [home / '.local/share/future-crash-look/RELEASE',
                   home / '.local/share/future-crash-look/maintenance/installed-release.json']
    result = []
    for path in sorted(set(candidates)):
        if not path.exists() and not path.is_symlink(): continue
        relative = str(path.relative_to(home))
        if (path.is_symlink() or any(p.is_symlink() for p in path.parents if p != home and home in p.parents)
                or not path.is_file() or path.name in SKIP_NAMES or path.name.endswith(SKIP_SUFFIXES)):
            skipped.append(relative); continue
        result.append(path)
    return result, sorted(set(skipped))


def inventory(home):
    paths, skipped = sources(home)
    return {'schema': SCHEMA, 'files': len(paths), 'bytes': sum(p.stat().st_size for p in paths),
            'paths': [str(p.relative_to(home)) for p in paths], 'skipped': skipped, 'excluded': EXCLUDED}


def copy_state(source, destination):
    destination.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    if source.suffix == '.sqlite3':
        # Online backup includes committed WAL data without copying a live WAL.
        with contextlib.closing(sqlite3.connect(source.as_uri() + '?mode=ro', uri=True, timeout=10)) as live:
            with contextlib.closing(sqlite3.connect(destination)) as snapshot:
                live.backup(snapshot)
                if snapshot.execute('PRAGMA quick_check').fetchone()[0] != 'ok':
                    raise ValueError('SQLite recovery snapshot failed integrity check')
    else:
        for attempt in range(3):
            before = source.stat()
            fd = os.open(source, os.O_RDONLY | os.O_NOFOLLOW)
            with os.fdopen(fd, 'rb') as incoming, destination.open('wb') as outgoing:
                shutil.copyfileobj(incoming, outgoing)
            after = source.stat()
            if (before.st_ino, before.st_size, before.st_mtime_ns) == (after.st_ino, after.st_size, after.st_mtime_ns):
                break
        else: raise RuntimeError('State changed repeatedly during snapshot: ' + str(source))
    os.chmod(destination, 0o600)


def capsule_owner(home):
    # Separate OS accounts on one computer must never share a snapshot owner.
    home = Path(home)
    identity_path = home / '.config/future-crash-look/identity/node_ed25519.pub'
    if identity_path.is_file() and not identity_path.is_symlink():
        return 'fabric-' + hashlib.sha256(identity_path.read_bytes()).hexdigest()[:24]
    return socket.gethostname() + '-' + hashlib.sha256(str(home.resolve()).encode()).hexdigest()[:16]


def export(home, output):
    home = Path(home).resolve(); output = Path(output)
    output.mkdir(mode=0o700, parents=True, exist_ok=False)
    (output / 'home').mkdir(mode=0o700)
    lock = home / '.local/share/look/notebook/lock'
    with contextlib.ExitStack() as stack:
        if lock.exists():
            stream = stack.enter_context(lock.open('r'))
            fcntl.flock(stream, fcntl.LOCK_SH)
        paths, skipped = sources(home)
        rows = []
        for source in paths:
            relative = str(source.relative_to(home))
            destination = output / 'home' / relative
            copy_state(source, destination)
            rows.append({'path': relative, 'size': destination.stat().st_size, 'sha256': digest(destination)})
    manifest = {'schema': SCHEMA, 'created_at': time.time(), 'node': capsule_owner(home), 'label': socket.gethostname() + ' / ' + home.name,
                'files': rows, 'skipped': skipped, 'excluded': EXCLUDED,
                'consistency': 'SQLite online snapshots; notebook lock; other files checked individually. Not a global transaction.'}
    private_json(output / 'manifest.json', manifest)
    verify(output)
    return {'files': len(rows), 'bytes': sum(row['size'] for row in rows), 'node': manifest['node']}


def verify(output):
    output = Path(output)
    manifest = json.loads((output / 'manifest.json').read_text())
    if manifest.get('schema') != SCHEMA: raise ValueError('Unsupported recovery schema')
    seen = set()
    for row in manifest['files']:
        relative = row['path']; p = PurePosixPath(relative)
        if p.is_absolute() or '..' in p.parts or str(p) != relative or relative in seen:
            raise ValueError('Unsafe or duplicate recovery path')
        seen.add(relative)
        path = output / 'home' / relative
        if any(q.is_symlink() for q in (path, *path.parents) if q == output or output in q.parents) or not path.is_file():
            raise ValueError('Missing or redirected recovery file')
        if path.stat().st_size != row['size'] or digest(path) != row['sha256']:
            raise ValueError('Recovery checksum mismatch: ' + relative)
        if path.suffix == '.sqlite3':
            with contextlib.closing(sqlite3.connect(path.as_uri() + '?mode=ro', uri=True)) as db:
                if db.execute('PRAGMA quick_check').fetchone()[0] != 'ok':
                    raise ValueError('Restored database failed integrity check')
    return {'verified': True, 'files': len(seen)}


def mount_for(uuid):
    if not uuid or any(c not in '0123456789abcdefABCDEF-' for c in uuid):
        raise ValueError('Invalid filesystem UUID')
    if sys.platform == 'darwin':
        try:
            from . import recovery_setup
        except ImportError:
            import recovery_setup
        rows = [d for d in recovery_setup.mounted_drives(external_only=False) if str(d['uuid']).casefold() == uuid.casefold()]
        if len(rows) > 1: raise ValueError('Backup UUID does not identify exactly one mount')
        return Path(rows[0]['mount']) if rows else None
    findmnt = '/usr/bin/findmnt' if Path('/usr/bin/findmnt').is_file() else 'findmnt'
    result = subprocess.run([findmnt, '--json', '--source', 'UUID=' + uuid,
                             '--output', 'TARGET,SOURCE,FSTYPE,OPTIONS'], capture_output=True, text=True)
    if result.returncode != 0: return None
    rows = json.loads(result.stdout).get('filesystems', [])
    if len(rows) != 1: raise ValueError('Backup UUID does not identify exactly one mount')
    if 'rw' not in rows[0]['options'].split(','): raise ValueError('Backup drive is read-only')
    return Path(rows[0]['target'])


def repository(config):
    mount = mount_for(config['uuid'])
    if mount is None: return None
    # Requiring an actual mount prevents writing into an empty mount-point folder.
    if not mount.is_mount(): raise ValueError('Destination is not a mounted filesystem')
    relative = config['directory']
    if relative != 'FabricRecovery': raise ValueError('Unrecognized recovery directory')
    repo = mount / relative / 'repository'
    if any(p.is_symlink() for p in (mount, repo.parent, repo)):
        raise ValueError('Backup directory must not redirect elsewhere')
    return repo


def restic(home, repo, *arguments):
    key = root(home) / 'key'
    if key.is_symlink() or stat.S_IMODE(key.stat().st_mode) & 0o077:
        raise ValueError('Recovery key must be private (mode 600)')
    env = dict(os.environ)
    # Explicit CLI settings prevent inherited credentials from changing the repo.
    env.pop('RESTIC_PASSWORD', None); env.pop('RESTIC_PASSWORD_COMMAND', None)
    process = subprocess.run(['restic', '--repo', str(repo), '--password-file', str(key), '--cache-dir', str(Path(home)/'.cache/future-crash-look/recovery-restic'), *arguments],
                             env=env, capture_output=True, text=True)
    if process.returncode: raise RuntimeError('Restic failed: ' + process.stderr[-1500:])
    return process.stdout


def initialize(home, uuid):
    state = root(home)
    if state.is_symlink(): raise ValueError('Recovery configuration must not redirect elsewhere')
    state.mkdir(parents=True, exist_ok=True, mode=0o700)
    with (state / 'run.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        return _initialize(home, uuid)


def _initialize(home, uuid):
    if shutil.which('restic') is None: raise ValueError('Install restic first')
    home = Path(home)
    if (root(home) / 'destination.json').exists(): raise ValueError('Destination already configured')
    config = {'schema': SCHEMA, 'uuid': uuid, 'directory': 'FabricRecovery'}
    repo = repository(config)
    if repo is None: raise ValueError('Authorized backup drive is not mounted')
    if repo.parent.exists(): raise ValueError('FabricRecovery already exists; refusing to take ownership')
    if shutil.disk_usage(repo.parent.parent).free < MIN_FREE_BYTES: raise ValueError('Insufficient free space')
    root(home).mkdir(parents=True, exist_ok=True, mode=0o700)
    key = root(home) / 'key'
    fd = os.open(key, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    created_directory = False
    try:
        with os.fdopen(fd, 'w') as stream: stream.write(secrets.token_urlsafe(48) + '\n')
        repo.parent.mkdir(mode=0o700); created_directory = True
        private_json(repo.parent / 'destination.json', {'schema': SCHEMA, 'uuid': uuid})
        restic(home, repo, 'init')
        private_json(root(home) / 'destination.json', config)
    except BaseException:
        # Only the new directory/key created by this attempt can be rolled back.
        if created_directory and not repo.parent.is_symlink(): shutil.rmtree(repo.parent)
        key.unlink(missing_ok=True)
        raise
    return {'configured': True, 'repository': str(repo), 'key_file': str(key)}


def checked_repository(home):
    config = load_config(home); repo = repository(config)
    if repo is None: return None
    marker = json.loads((repo.parent / 'destination.json').read_text())
    if marker != {'schema': SCHEMA, 'uuid': config['uuid']}:
        raise ValueError('Destination authorization marker differs')
    return repo


def restore(home, output, snapshot='latest', host=None):
    output = Path(output).absolute()
    if output.exists() or output.is_symlink(): raise ValueError('Restore requires a new, empty destination')
    repo = checked_repository(home)
    if repo is None: raise ValueError('Backup drive is disconnected')
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.fabric-restore-', dir=output.parent) as folder:
        os.chmod(folder, 0o700)
        owner = host or capsule_owner(home)
        if host is None:
            snapshots = json.loads(restic(home, repo, 'snapshots', '--json', '--host', owner, '--tag', 'fabric-essential'))
            if not snapshots: owner = socket.gethostname()  # Read snapshots made before account isolation.
        restic(home, repo, 'restore', snapshot, '--target', folder, '--host', owner, '--tag', 'fabric-essential')
        matches = list(Path(folder).rglob('manifest.json'))
        matches = [p for p in matches if (p.parent / 'home').is_dir()]
        if len(matches) != 1: raise ValueError('Snapshot lacks one recovery manifest')
        report = verify(matches[0].parent)
        shutil.move(str(matches[0].parent), output)
        # Keys remain inert; never install into the live home or start daemons.
        os.chmod(output, 0o700)
    return {**report, 'output': str(output), 'activated': False}


def backup(home, *, due=False):
    home = Path(home); state = root(home)
    state.mkdir(parents=True, exist_ok=True, mode=0o700)
    with (state / 'run.lock').open('a') as lock:
        try: fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError: return {'skipped': 'backup already running'}
        repo = checked_repository(home)
        if repo is None: return {'skipped': 'backup drive disconnected'}
        receipt_path = state / 'last-backup.json'
        receipt = json.loads(receipt_path.read_text()) if receipt_path.exists() else {}
        if due and time.time() - receipt.get('verified_at', 0) < DAILY_SECONDS:
            return {'skipped': 'daily recovery already verified'}
        if shutil.disk_usage(repo).free < MIN_FREE_BYTES: raise ValueError('Insufficient backup space')
        with tempfile.TemporaryDirectory(prefix='fabric-recovery-') as folder:
            snapshot = Path(folder) / 'snapshot'
            export(home, snapshot)
            return store_capsule(home, repo, snapshot, receipt_path)


def store_capsule(home, repo, capsule, receipt_path):
    verify(capsule)
    manifest = json.loads((capsule / 'manifest.json').read_text())
    host = manifest['node']
    if not isinstance(host, str) or not host or len(host) > 255:
        raise ValueError('Invalid capsule owner')
    restic(home, repo, 'backup', str(capsule), '--host', host, '--tag', 'fabric-essential')
    restic(home, repo, 'check', '--read-data')
    with tempfile.TemporaryDirectory(prefix='fabric-restore-check-') as folder:
        restore(home, Path(folder) / 'verified', host=host)
    receipt = {'files': len(manifest['files']), 'bytes': sum(row['size'] for row in manifest['files']),
               'node': host, 'label': manifest.get('label') or host, 'verified_at': time.time(), 'uuid': load_config(home)['uuid'],
               'restore_tested': True, 'scope': 'essential state of this node', 'excluded': EXCLUDED}
    private_json(receipt_path, receipt)
    return receipt


def receive(home, stream):
    """SSH-only receiver. Never expose recovery keys through the Fabric HTTP API."""
    with tempfile.TemporaryDirectory(prefix='fabric-receive-') as folder:
        capsule = Path(folder) / 'snapshot'; capsule.mkdir(mode=0o700)
        (capsule / 'home').mkdir(mode=0o700)
        with tempfile.TemporaryFile() as archive:
            size = 0
            while True:
                block = stream.read(1024 * 1024)
                if not block: break
                size += len(block)
                if size > MAX_CAPSULE_BYTES: raise ValueError('Recovery capsule exceeds transfer limit')
                archive.write(block)
            archive.seek(0)
            seen = set(); total = 0
            with tarfile.open(fileobj=archive, mode='r:') as tar:
                for member in tar:
                    p = PurePosixPath(member.name)
                    if (not member.isfile() or p.is_absolute() or '..' in p.parts or str(p) != member.name
                            or not p.parts or member.name in seen or not (member.name == 'manifest.json' or p.parts[0] == 'home')):
                        raise ValueError('Unsafe recovery archive member')
                    seen.add(member.name); total += member.size
                    if total > MAX_CAPSULE_BYTES: raise ValueError('Recovery capsule exceeds size limit')
                    destination = capsule / member.name
                    destination.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
                    with tar.extractfile(member) as incoming, destination.open('xb') as outgoing:
                        shutil.copyfileobj(incoming, outgoing)
                    os.chmod(destination, 0o600)
        verify(capsule)
        manifest = json.loads((capsule / 'manifest.json').read_text())
        expected = {'manifest.json'} | {'home/' + row['path'] for row in manifest['files']}
        if seen != expected: raise ValueError('Archive differs from recovery inventory')
        state = root(home)
        with (state / 'run.lock').open('a') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            repo = checked_repository(home)
            if repo is None: raise ValueError('Backup drive disconnected')
            if shutil.disk_usage(repo).free < MIN_FREE_BYTES: raise ValueError('Insufficient backup space')
            receipt_path = state / ('received-' + hashlib.sha256(manifest['node'].encode()).hexdigest()[:16] + '.json')
            return store_capsule(home, repo, capsule, receipt_path)


def send(home, target, due=False):
    if not target or target.startswith('-') or not re.fullmatch(r'[A-Za-z0-9_][A-Za-z0-9_.-]*@[A-Za-z0-9][A-Za-z0-9.-]*', target):
        raise ValueError('Use an SSH user@host destination')
    sent = root(home) / 'last-sent.json'
    if due and sent.exists():
        last = json.loads(sent.read_text())
        if last.get('destination') == target and time.time() - last.get('verified_at', 0) < DAILY_SECONDS:
            return {'skipped': 'daily recovery already verified'}
    with tempfile.TemporaryDirectory(prefix='fabric-send-') as folder:
        capsule = Path(folder) / 'snapshot'; report = export(home, capsule)
        with tempfile.TemporaryFile() as archive:
            with tarfile.open(fileobj=archive, mode='w:') as tar:
                tar.add(capsule / 'manifest.json', arcname='manifest.json', recursive=False)
                manifest = json.loads((capsule / 'manifest.json').read_text())
                for row in manifest['files']:
                    tar.add(capsule / 'home' / row['path'], arcname='home/' + row['path'], recursive=False)
            if archive.tell() > MAX_CAPSULE_BYTES: raise ValueError('Recovery capsule exceeds transfer limit')
            archive.seek(0)
            keychain = ['-o', 'UseKeychain=yes'] if sys.platform == 'darwin' else []
            result = subprocess.run(['ssh', *keychain, '-o', 'BatchMode=yes', '-o', 'StrictHostKeyChecking=yes',
                                     '-o', 'ConnectTimeout=10', target, '~/.local/bin/fcl-recovery receive'],
                                    stdin=archive, capture_output=True, text=True)
            if result.returncode: raise RuntimeError('Recovery transfer failed: ' + result.stderr[-1500:] + result.stdout[-1500:])
            receipt = json.loads(result.stdout)
            if not receipt.get('restore_tested'): raise ValueError('Receiver did not verify recovery')
            private_json(root(home) / 'last-sent.json', {**receipt, 'destination': target})
            return receipt



def stream_capsule(home, outgoing):
    with tempfile.TemporaryDirectory(prefix='fabric-stream-') as folder:
        capsule = Path(folder) / 'snapshot'; report = export(home, capsule)
        if report['bytes'] > MAX_CAPSULE_BYTES - 1024 * 1024:
            raise ValueError('Recovery capsule exceeds transfer limit')
        with tarfile.open(fileobj=outgoing, mode='w|') as tar:
            tar.add(capsule / 'manifest.json', arcname='manifest.json', recursive=False)
            manifest = json.loads((capsule / 'manifest.json').read_text())
            for row in manifest['files']:
                tar.add(capsule / 'home' / row['path'], arcname='home/' + row['path'], recursive=False)


def collect(home, source, target, due=False):
    for value in (source, target):
        if not value or value.startswith('-') or not re.fullmatch(r'[A-Za-z0-9_][A-Za-z0-9_.-]*@[A-Za-z0-9][A-Za-z0-9.-]*', value):
            raise ValueError('Use an SSH user@host source and destination')
    receipt_path = root(home) / ('collected-' + hashlib.sha256(source.encode()).hexdigest()[:16] + '.json')
    if due and receipt_path.exists():
        receipt = json.loads(receipt_path.read_text())
        if receipt.get('destination') == target and time.time() - receipt.get('verified_at', 0) < DAILY_SECONDS:
            return {'skipped': 'daily recovery already verified'}
    options = ['-o', 'BatchMode=yes', '-o', 'StrictHostKeyChecking=yes', '-o', 'ConnectTimeout=10']
    if sys.platform == 'darwin': options += ['-o', 'UseKeychain=yes']
    origin = subprocess.Popen(['ssh', *options, source, '~/.local/bin/fcl-recovery stream'],
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    try:
        result = subprocess.run(['ssh', *options, target, '~/.local/bin/fcl-recovery receive'],
                                stdin=origin.stdout, capture_output=True, text=True)
        origin.stdout.close()
        _, error = origin.communicate(timeout=30)
        if origin.returncode or result.returncode:
            raise RuntimeError('Recovery collection failed: ' + error.decode(errors='replace')[-1500:] + result.stderr[-1500:] + result.stdout[-1500:])
        receipt = json.loads(result.stdout)
        if not receipt.get('restore_tested'): raise ValueError('Receiver did not verify recovery')
        private_json(receipt_path, {**receipt, 'source': source, 'destination': target})
        return receipt
    finally:
        if origin.poll() is None: origin.kill(); origin.wait()



def status(home):
    if not (root(home) / 'destination.json').exists():
        sent = root(home) / 'last-sent.json'
        return {'configured': False, 'role': 'contributor' if sent.exists() else 'unconfigured',
                'last_sent': json.loads(sent.read_text()) if sent.exists() else None,
                'collected': [json.loads(p.read_text()) for p in sorted(root(home).glob('collected-*.json'))]}
    config = load_config(home)
    path = root(home) / 'last-backup.json'
    return {'configured': True, 'role': 'destination owner', 'uuid': config['uuid'], 'connected': checked_repository(home) is not None,
            'key_file': str(root(home) / 'key'),
            'last_backup': json.loads(path.read_text()) if path.exists() else None,
            'received': [json.loads(p.read_text()) for p in sorted(root(home).glob('received-*.json'))]}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    sub.add_parser('inventory'); status_parser = sub.add_parser('status'); status_parser.add_argument('--json', action='store_true')
    sub.add_parser('receive'); sub.add_parser('stream'); sub.add_parser('menu'); sub.add_parser('drives').add_argument('--json', action='store_true')
    sub.add_parser('scheduled')
    for action in ('add', 'configure'):
        setup = sub.add_parser(action, help='Guided connected-drive, contributor and schedule setup')
        setup.add_argument('--mount'); setup.add_argument('--key-copy'); setup.add_argument('--source', action='append', default=[])
        setup.add_argument('--schedule', choices=['daily','manual'], default='daily'); setup.add_argument('--yes', action='store_true'); setup.add_argument('--json', action='store_true')
    spare = sub.add_parser('key-copy'); spare.add_argument('output')
    gather = sub.add_parser('collect'); gather.add_argument('source'); gather.add_argument('target'); gather.add_argument('--due', action='store_true')
    ship = sub.add_parser('send'); ship.add_argument('target'); ship.add_argument('--due', action='store_true')
    init = sub.add_parser('init'); init.add_argument('--uuid', required=True)
    run = sub.add_parser('run'); run.add_argument('--due', action='store_true'); run.add_argument('--json', action='store_true')
    out = sub.add_parser('export'); out.add_argument('output')
    check = sub.add_parser('verify'); check.add_argument('directory')
    recover = sub.add_parser('restore'); recover.add_argument('output'); recover.add_argument('--snapshot', default='latest'); recover.add_argument('--host')
    args = parser.parse_args(argv); home = Path.home()
    try:
        try:
            from . import recovery_setup as setup
        except ImportError:
            import recovery_setup as setup
        if args.command == 'menu':
            if not sys.stdin.isatty(): setup.show_status(home); return 0
            setup.menu(home); return 0
        if args.command in {'add','configure'}:
            if args.command == 'add' and (root(home)/'destination.json').exists():
                if args.json: print(json.dumps({'configured':True,'already_configured':True,'next':'Use configure for contributors and schedule'},indent=2))
                else: setup.show_status(home); print('A drive is already configured; use configure for contributors and schedule.')
                return 0
            if args.yes:
                result = setup.configure(home, mount=args.mount, key_copy=args.key_copy, sources=args.source, daily=args.schedule=='daily')
            elif sys.stdin.isatty(): result = setup.wizard(home, updating=args.command=='configure')
            else: raise ValueError('Run setup in a terminal, or provide --yes --mount PATH --key-copy NEW_FILE')
            if args.json: print(json.dumps(result, indent=2))
            else: setup.report(result)
            return 1 if result.get('verified') is False else 0
        if args.command == 'drives':
            result = setup.mounted_drives()
            if args.json: print(json.dumps(result, indent=2)); return 0
            for number, drive in enumerate(result,1): print(f"{number}. {setup.clean(drive['name'])} · {drive['free_bytes']/1024**3:.0f} GiB free · {setup.clean(drive['mount'])}")
            if not result: print('No writable external drive mounted. Connect/unlock one in your file manager.')
            return 0
        if args.command == 'status' and not args.json: setup.show_status(home); return 0
        if args.command == 'key-copy':
            print('Spare recovery key saved: ' + setup.copy_key(home,args.output)); return 0
        if args.command == 'scheduled':
            result = setup.run_configured(home)
            print(json.dumps(result,indent=2)); return 1 if result.get('verified') is False else 0
        if args.command == 'stream': stream_capsule(home, sys.stdout.buffer); return 0
        if args.command == 'collect': result = collect(home, args.source, args.target, args.due)
        elif args.command == 'inventory': result = inventory(home)
        elif args.command == 'status': result = status(home)
        elif args.command == 'init': result = initialize(home, args.uuid)
        elif args.command == 'run': result = setup.run_configured(home, due=args.due) if (root(home)/'setup.json').exists() else backup(home, due=args.due)
        elif args.command == 'send': result = send(home, args.target, args.due)
        elif args.command == 'receive': result = receive(home, sys.stdin.buffer)
        elif args.command == 'export': result = export(home, args.output)
        elif args.command == 'verify': result = verify(Path(args.directory).absolute())
        else: result = restore(home, args.output, args.snapshot, args.host)
        if args.command == 'run' and not args.json: setup.report(result)
        else: print(json.dumps(result, indent=2))
        return 1 if result.get('verified') is False else 0
    except (EOFError, KeyboardInterrupt):
        print('Backup setup cancelled.'); return 130
    except (OSError, ValueError, RuntimeError, sqlite3.Error, tarfile.TarError, subprocess.TimeoutExpired) as exc:
        if args.command in {'add','configure','drives','menu','status','key-copy'} and not getattr(args,'json',False):
            print('BACKUP · ' + setup.clean(exc))
        else: print(json.dumps({'ok': False, 'error': str(exc)}), file=sys.stderr if args.command == 'stream' else sys.stdout)
        return 1


if __name__ == '__main__': raise SystemExit(main())
