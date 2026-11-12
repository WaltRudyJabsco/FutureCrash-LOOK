"""Portable drive identities. Registration never initializes or schedules backups."""
from __future__ import annotations
import argparse
import copy
import fcntl
import json
import os
from pathlib import Path, PurePosixPath
import platform
import subprocess
import shlex
import tempfile
import threading
import time
import urllib.request
import uuid

MARKER = '.fabric-storage.json'
REFRESH_SECONDS = 60
MAX_RECORDS = 256
MAX_JSON_BYTES = 262144
_CACHE = {'registered': [], 'attached': [], 'peers': [], 'checked_at': 0}
_LOCK = threading.RLock()


def config_dir(home=None):
    return Path(home or Path.home()) / '.config/future-crash-look/storage'


def read_json(path):
    if path.is_symlink():
        raise ValueError('Storage metadata must not be a symlink')
    with path.open('rb') as stream:
        raw = stream.read(MAX_JSON_BYTES + 1)
    if len(raw) > MAX_JSON_BYTES:
        raise ValueError('Storage metadata is too large')
    return json.loads(raw)


def validate(record):
    if not isinstance(record, dict) or record.get('schema') != 1:
        raise ValueError('Unsupported storage registration')
    uuid.UUID(record['id'])
    if record.get('role') not in {'backup', 'travel'}:
        raise ValueError('Choose backup or travel')
    name = record.get('name', '')
    if not isinstance(name, str) or not name.strip() or len(name) > 80 or any(ord(c) < 32 for c in name):
        raise ValueError('Use a short, readable drive name')
    if not isinstance(record.get('volume_uuid'), str) or not record['volume_uuid']:
        raise ValueError('A filesystem UUID is required')
    if record.get('platform') not in {'Darwin', 'Linux'}:
        raise ValueError('Unknown registration platform')
    paths = record.get('paths')
    if not isinstance(paths, list) or len(paths) > 32:
        raise ValueError('Invalid library folders')
    for value in paths:
        if not isinstance(value, str) or not value or '\\' in value or any(ord(c) < 32 for c in value):
            raise ValueError('Invalid library folder')
        p = PurePosixPath(value)
        if p.is_absolute() or '..' in p.parts or value in {'.', ''}:
            raise ValueError('Library folders must stay inside the drive')
    if record['role'] == 'backup' and paths:
        raise ValueError('Backup repositories are not browsable travel libraries')
    if record['role'] == 'travel' and not paths:
        raise ValueError('Choose at least one travel-library folder')
    expected = {'schema', 'id', 'name', 'role', 'volume_uuid', 'platform', 'paths'}
    if set(record) != expected:
        raise ValueError('Unexpected registration fields')
    return record


def registry(home=None):
    path = config_dir(home) / 'registry.json'
    if not path.exists():
        return []
    records = read_json(path)
    if not isinstance(records, list) or len(records) > MAX_RECORDS:
        raise ValueError('Invalid storage registry')
    result = [validate(r) for r in records]
    if len({r['id'] for r in result}) != len(result):
        raise ValueError('Duplicate registration identity')
    return result


def atomic_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix='.storage-', dir=path.parent)
    try:
        with os.fdopen(fd, 'w') as stream:
            json.dump(data, stream, indent=2)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp): os.unlink(tmp)


def merge(records, home=None):
    """Only the authenticated peer caller may supply registrations here."""
    if not isinstance(records, list) or len(records) > MAX_RECORDS:
        raise ValueError('Invalid peer registry')
    incoming = [validate(r) for r in records]
    directory = config_dir(home)
    directory.mkdir(parents=True, exist_ok=True)
    with (directory / 'registry.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        current = {r['id']: r for r in registry(home)}
        for record in incoming:
            if record['id'] in current and current[record['id']] != record:
                raise ValueError('Conflicting drive identity; existing registration preserved')
            current[record['id']] = record
        if len(current) > MAX_RECORDS: raise ValueError('Storage registry is full')
        atomic_json(directory / 'registry.json', list(current.values()))


def drives():
    try:
        from . import recovery_setup
    except ImportError:
        import recovery_setup
    return recovery_setup.mounted_drives(external_only=False, include_readonly=True)


def library_path(mount, relative):
    root = Path(mount).resolve()
    path = (root / relative).resolve()
    if not path.is_relative_to(root) or path == root:
        raise ValueError('Library folder escapes the registered drive')
    if not path.is_dir(): raise ValueError('Library folder is missing')
    return str(path)


def scan(home=None, inventory=None):
    known = {r['id']: r for r in registry(home)}
    attached = []
    for drive in drives() if inventory is None else inventory:
        marker = Path(drive['mount']) / MARKER
        if not marker.exists(): continue
        row = {'mount': drive['mount'], 'volume_uuid': drive['uuid'], 'state': 'unregistered'}
        try:
            record = validate(read_json(marker))
            row.update(id=record['id'], name=record['name'], role=record['role'])
            if known.get(record['id']) != record:
                row['state'] = 'unregistered or conflicting marker'
            elif record['platform'] == platform.system() and record['volume_uuid'].casefold() != drive['uuid'].casefold():
                row['state'] = 'filesystem identity changed'
            else:
                row['state'] = 'available'
                row['folders'] = [library_path(drive['mount'], p) for p in record['paths']]
                row['free_bytes'] = drive.get('free_bytes')
        except (ValueError, KeyError, TypeError, OSError) as exc:
            row['state'] = 'invalid'; row['error'] = str(exc)
        attached.append(row)
    for row in attached:
        if row.get('id') and sum(r.get('id') == row['id'] for r in attached) > 1:
            row['state'] = 'duplicate identity'; row.pop('folders', None)
    return {'registered': list(known.values()), 'attached': attached, 'checked_at': time.time()}


def register(mount, name, role, paths=(), home=None, inventory=None, commit=False):
    candidates = drives() if inventory is None else inventory
    matches = [d for d in candidates if Path(d['mount']) == Path(mount)]
    if len(matches) != 1: raise ValueError('Choose a currently mounted drive')
    drive = matches[0]
    record = validate(dict(schema=1, id=str(uuid.uuid4()), name=name, role=role,
                           volume_uuid=drive['uuid'], platform=platform.system(), paths=list(paths)))
    marker = Path(mount) / MARKER
    if marker.exists() or marker.is_symlink():
        raise ValueError('This drive already has a marker. Sync its trusted registration instead of overwriting it')
    for p in paths: library_path(mount, p)
    plan = {'registration': record, 'mount': mount, 'changes': [str(marker), str(config_dir(home) / 'registry.json')],
            'preserved': 'All content, backup repositories, credentials and schedules. No data copied.'}
    if not commit: return plan
    # Exclusive creation prevents overwriting a marker installed by another registrar.
    with marker.open('x') as stream:
        json.dump(record, stream, indent=2); stream.flush(); os.fsync(stream.fileno())
    try:
        merge([record], home)
    except Exception:
        marker.unlink()
        raise
    if read_json(marker) != record: raise ValueError('Drive registration verification failed')
    return plan


def snapshot():
    with _LOCK:
        data = copy.deepcopy(_CACHE)
    if time.time() - data['checked_at'] > REFRESH_SECONDS * 3:
        data.update(attached=[], peers=[], stale=True)
    return data


def refresh(peers=(), fetch=None, home=None):
    observations = []
    for peer in peers:
        if not peer.get('trusted') or fetch is None: continue
        try:
            remote = fetch(peer, '/v1/storage/local')
            merge(remote.get('registered', []), home)
            # Never propagate observations from a third node or an expired cache.
            fresh = 0 <= time.time() - float(remote.get('checked_at', 0)) <= REFRESH_SECONDS * 3
            observations.append({'node': peer.get('name'), 'reachable': True,
                                 'attached': remote.get('attached', []) if fresh else [], 'fresh': fresh})
        except Exception as exc:
            observations.append({'node': peer.get('name'), 'reachable': False, 'error': str(exc), 'attached': []})
    local = scan(home)
    local['peers'] = observations
    with _LOCK: _CACHE.update(local)
    return local


def worker(peers, fetch):
    while True:
        try: refresh(peers(), fetch)
        except Exception as exc:
            with _LOCK:
                _CACHE.update(attached=[], checked_at=0, error=str(exc))
        time.sleep(REFRESH_SECONDS)


def request(path='/v1/storage'):
    with urllib.request.urlopen('http://127.0.0.1:7332' + path, timeout=30) as response:
        return json.load(response)


def resolve(data, selector):
    records = [r for r in data['registered'] if selector.casefold() in {r['id'].casefold(), r['name'].casefold()}]
    if len(records) != 1: raise ValueError('Choose a unique drive name or ID')
    record = records[0]
    choices = [(None, r) for r in data['attached'] if r.get('id') == record['id']]
    for peer in data.get('peers', []):
        choices += [(peer['node'], r) for r in peer['attached'] if r.get('id') == record['id']]
    if len(choices) != 1 or choices[0][1]['state'] != 'available':
        raise ValueError('Drive is disconnected, stale, or has conflicting identities')
    if record['role'] == 'backup':
        raise ValueError('Backup recognized. Use lk fabric backup on its configured owner; credentials and schedules do not move automatically')
    node, drive = choices[0]
    return [f'@{node}:{p}' if node else p for p in drive['folders']]


def main(argv=None):
    parser = argparse.ArgumentParser(description='Registered Fabric backup and travel drives. No automatic backup takeover or media copying.')
    sub = parser.add_subparsers(dest='command')
    sub.add_parser('status'); sub.add_parser('drives'); sub.add_parser('sync')
    reg = sub.add_parser('register')
    reg.add_argument('--mount'); reg.add_argument('--name')
    reg.add_argument('--role', choices=['backup', 'travel'])
    reg.add_argument('--path', action='append', default=[]); reg.add_argument('--yes', action='store_true')
    for command in ['open', 'resolve']:
        item = sub.add_parser(command); item.add_argument('drive'); item.add_argument('--folder', type=int, default=1)
    args = parser.parse_args(argv)
    try:
        if args.command == 'drives':
            for i, d in enumerate(drives(), 1): print(f"{i}. {d['name']} · {d['mount']} · {d['filesystem']}")
            print('Register a mounted drive with: lk fabric storage register --mount PATH --name NAME --role backup|travel [--path FOLDER]')
            return 0
        if args.command == 'register':
            if not args.mount:
                available = drives()
                for i, d in enumerate(available, 1): print(f"{i}. {d['name']} · {d['filesystem']} · {d['free_bytes']//(1024**3)} GiB free")
                if not available: raise ValueError('No mounted data drives found')
                choice = int(input('Choose drive number: '))
                if not 1 <= choice <= len(available): raise ValueError('Choose a listed drive')
                args.mount = available[choice-1]['mount']
                args.name = args.name or input('Drive name: ').strip() or available[choice-1]['name']
                args.role = args.role or input('Role (backup/travel): ').strip().lower()
                if args.role == 'travel' and not args.path:
                    args.path = [p.strip() for p in input('Existing library folders, comma separated (for example Books, Music): ').split(',')]
            if not args.name or not args.role: raise ValueError('Supply --name and --role, or run register without options')
            print(json.dumps(register(args.mount, args.name, args.role, args.path, commit=args.yes), indent=2))
            if args.yes:
                print('Registered. Trusted nodes learn this identity on their next refresh.')
            else:
                command = ['lk', 'fabric', 'storage', 'register', '--mount', args.mount, '--name', args.name, '--role', args.role]
                for folder in args.path: command.extend(['--path', folder])
                print('No changes made. To apply this plan:\n' + shlex.join(command + ['--yes']))
            return 0
        try: data = request('/v1/storage/refresh' if args.command in {'sync', 'open', 'resolve'} else '/v1/storage')
        except OSError:
            data = scan(); data['peers'] = []
            print('Fabric service unavailable; showing locally registered drives only.')
        if args.command in {'open', 'resolve'}:
            folders = resolve(data, args.drive)
            if args.command == 'resolve': print('\n'.join(folders)); return 0
            if args.folder < 1 or args.folder > len(folders): raise ValueError('Choose a listed folder number')
            return subprocess.call([str(Path.home()/'.local/bin/lk'), folders[args.folder-1]])
        for r in data['registered']:
            locations = [('this node', a) for a in data['attached'] if a.get('id') == r['id']]
            for p in data.get('peers', []): locations += [(p['node'], a) for a in p['attached'] if a.get('id') == r['id']]
            text = '; '.join(f"{n}: {a['state']}" for n,a in locations) or 'not currently located'
            print(f"{r['name']} · {r['role']} · {text}")
        if not data['registered']: print('No registered drives. Run lk fabric storage drives to choose one.')
        print('Commands: drives · register --help · sync · resolve NAME · open NAME [--folder N]')
        return 0
    except (ValueError, KeyError, OSError) as exc:
        print(f'Storage: {exc}'); return 1

if __name__ == '__main__': raise SystemExit(main())
