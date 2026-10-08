"""Explicit, paired-node runtime updates. No shell edits, packages, or host reboot.

A detached local helper stages approved bytes, waits for an idle worker, retains
old files, and verifies the restarted runtime. System services own the lifecycle.
"""
from __future__ import annotations
import argparse
import fcntl
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import platform
import shutil
import subprocess
import sys
import time
import uuid
import zipfile
import urllib.request

MAX_BUNDLE = 32 * 1024 * 1024
PROTOCOL = 1
TERMINAL = {'healthy', 'rolled_back', 'failed'}


def root(): return Path.home() / '.local/share/future-crash-look/maintenance'
def registry(): return root() / 'installed-release.json'
def digest(data): return hashlib.sha256(data).hexdigest()


def atomic_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name('.' + path.name + '.' + uuid.uuid4().hex)
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, 'w') as out: json.dump(value, out, sort_keys=True)
    os.replace(tmp, path)


def allowed(relative):
    p = PurePosixPath(relative)
    if p.is_absolute() or '..' in p.parts or str(p) != relative: return False
    parent = str(p.parent)
    if parent == '.local/share/future-crash-look/core': return p.suffix == '.py'
    if parent == '.local/share/future-crash-look': return p.name == 'RELEASE'
    if parent == '.local/share/look': return p.suffix == '.py' or p.name == 'lk'
    if parent == '.local/share/signal-window':
        return p.name in {'server.py', 'app.js', 'media-session.js', 'index.html', 'style.css'}
    if parent == '.local/share/future-crash': return p.name == 'future_crash.py'
    if parent == '.local/bin':
        return p.name in {'fcl-node', 'fcl-ingress', 'fcl-tailcat', 'fcl-rendezvous', 'fcl-openjev-worker', 'future-crash'}
    return False


def destination(relative):
    if not allowed(relative): raise ValueError('release contains a non-runtime destination')
    path = Path.home() / relative
    # Neither a destination nor its ancestors may redirect a deployment elsewhere.
    if any(parent.is_symlink() for parent in (path, *path.parents) if parent != Path.home() and Path.home() in parent.parents) or not path.resolve().is_relative_to(Path.home().resolve()):
        raise ValueError('runtime destination redirects outside the install')
    return path


def register_install(source):
    source = Path(source)
    mappings = []
    for p in (source / 'core').glob('*.py'):
        mappings.append((p, '.local/share/future-crash-look/core/' + p.name))
    for p in (source / 'core').glob('fcl-*'):
        if p.is_file(): mappings.append((p, '.local/bin/' + p.name))
    for p in (source / 'look').glob('*.py'):
        mappings.append((p, '.local/share/look/' + p.name))
    mappings.append((source / 'look/lk', '.local/share/look/lk'))
    mappings.append((source / 'VERSION', '.local/share/future-crash-look/RELEASE'))
    mappings += [(source / 'signal-window' / n, '.local/share/signal-window/' + n)
                 for n in ('server.py', 'app.js', 'media-session.js', 'index.html', 'style.css')]
    mappings += [(source / 'future-crash' / n, target) for n, target in
                 [('future_crash.py', '.local/share/future-crash/future_crash.py'), ('future-crash', '.local/bin/future-crash')]]
    files = []
    for src, relative in mappings:
        if not allowed(relative): continue
        dst = destination(relative)
        if not dst.is_file() or not src.is_file(): continue
        data = src.read_bytes()
        if dst.read_bytes() != data: raise ValueError('installed runtime differs from checkout: ' + relative)
        files.append({'path': relative, 'sha256': digest(data), 'size': len(data), 'mode': dst.stat().st_mode & 0o777})
    required = {'.local/share/look/lk', '.local/share/look/lo_history.py',
                '.local/share/future-crash-look/core/node.py', '.local/share/future-crash-look/core/maintenance.py'}
    if not required.issubset({f['path'] for f in files}): raise ValueError('runtime installation is incomplete')
    try:
        result = subprocess.run(['git', '-C', str(source), 'rev-parse', 'HEAD'], capture_output=True, text=True)
        commit = result.stdout.strip() if result.returncode == 0 else None
    except OSError: commit = None
    manifest = {'protocol': PROTOCOL, 'release': (source / 'VERSION').read_text().strip(),
                'commit': commit, 'files': sorted(files, key=lambda f: f['path'])}
    atomic_json(registry(), manifest)
    return manifest


def bundle():
    manifest = json.loads(registry().read_text())
    out = io.BytesIO()
    with zipfile.ZipFile(out, 'w', zipfile.ZIP_STORED) as z:
        def put(name, data):
            info = zipfile.ZipInfo(name, (1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_STORED
            info.create_system = 3
            info.external_attr = 0o600 << 16
            z.writestr(info, data)
        put('manifest.json', json.dumps(manifest, sort_keys=True, separators=(',', ':')).encode())
        for f in manifest['files']:
            data = destination(f['path']).read_bytes()
            if digest(data) != f['sha256']: raise ValueError('installed code changed; reinstall before distributing updates')
            put(f['path'], data)
    data = out.getvalue()
    if len(data) > MAX_BUNDLE: raise ValueError('runtime bundle exceeds limit')
    return manifest, data


def release_info():
    try:
        manifest, data = bundle()
        return {'available': True, 'protocol': PROTOCOL, 'release': manifest['release'],
                'commit': manifest.get('commit'), 'digest': digest(data), 'files': len(manifest['files']), 'bytes': len(data)}
    except (OSError, ValueError, KeyError) as exc:
        return {'available': False, 'protocol': PROTOCOL, 'error': str(exc),
                'hint': 'run the unified installer once to register this runtime'}


def validate_bundle(data, expected):
    try: return _validate_bundle(data, expected)
    except (KeyError, TypeError, SyntaxError, zipfile.BadZipFile, RuntimeError) as exc:
        raise ValueError("invalid runtime release") from exc


def _validate_bundle(data, expected):
    if len(data) > MAX_BUNDLE or digest(data) != expected: raise ValueError('approved release digest mismatch')
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        infos = z.infolist()
        if len(infos) > 256 or sum(i.file_size for i in infos) > MAX_BUNDLE: raise ValueError('release exceeds unpacked limits')
        if len({i.filename for i in infos}) != len(infos): raise ValueError('duplicate archive members')
        manifest = json.loads(z.read('manifest.json'))
        if manifest.get('protocol') != PROTOCOL: raise ValueError('unsupported update protocol')
        files = manifest.get('files')
        if not isinstance(files, list) or not files: raise ValueError('empty runtime release')
        paths = [f['path'] for f in files]
        if len(set(paths)) != len(paths) or set(z.namelist()) != {'manifest.json', *paths}: raise ValueError('release inventory mismatch')
        required = {'.local/share/look/lk', '.local/share/future-crash-look/core/node.py',
                    '.local/share/future-crash-look/core/maintenance.py'}
        if not required.issubset(paths): raise ValueError('missing runtime entry points')
        payload = {}
        for f in files:
            destination(f['path'])
            if f.get('mode') not in {0o644, 0o755}: raise ValueError('unsupported runtime mode')
            raw = z.read(f['path'])
            if len(raw) != f['size'] or digest(raw) != f['sha256']: raise ValueError('release file checksum mismatch')
            if f['path'].endswith('.py') or f['path'] == '.local/share/look/lk':
                compile(raw, f['path'], 'exec')
            payload[f['path']] = raw
    return manifest, payload


def receipt(job):
    if not job or any(c not in '0123456789abcdef' for c in job) or len(job) != 32: raise ValueError('invalid maintenance job')
    return json.loads((root() / 'jobs' / job / 'receipt.json').read_text())


def status():
    try:
        job = json.loads((root() / 'active.json').read_text())['job']
        return receipt(job)
    except (OSError, ValueError, KeyError): return {'state': 'idle'}


def draining():
    current = status()
    if current.get('state') not in {'draining', 'installing', 'restarting', 'verifying', 'rolling_back'}: return False
    try: os.kill(int(current['pid']), 0)
    except (OSError, ValueError, KeyError): return False
    return True


def schedule(action, *, data=None, expected=None):
    if action not in {'update', 'restart'}: raise ValueError('unsupported maintenance action')
    root().mkdir(parents=True, exist_ok=True)
    with open(root() / 'schedule.lock', 'a') as lock:
        os.chmod(lock.name, 0o600)
        fcntl.flock(lock, fcntl.LOCK_EX)
        current = status()
        if current.get('state') not in TERMINAL | {'idle'}:
            try: os.kill(int(current['pid']), 0)
            except (OSError, ValueError, KeyError): pass
            else: raise ValueError('maintenance already in progress')
        if action == 'update': validate_bundle(data, expected)
        job = uuid.uuid4().hex
        folder = root() / 'jobs' / job
        folder.mkdir(parents=True, mode=0o700)
        if data is not None: (folder / 'release.zip').write_bytes(data)
        config = {'job': job, 'action': action, 'digest': expected, 'state': 'staged', 'created': time.time()}
        atomic_json(folder / 'receipt.json', config)
        atomic_json(root() / 'active.json', {'job': job})
        # Run a pinned copy: replacing the installed maintenance module cannot kill recovery.
        shutil.copyfile(__file__, folder / 'runner.py')
        with open(folder / 'runner.log', 'ab') as log:
            try:
                proc = subprocess.Popen([sys.executable, str(folder / 'runner.py'), '--run-job', job],
                                        stdin=subprocess.DEVNULL, stdout=log, stderr=log, start_new_session=True)
            except OSError as exc:
                atomic_json(folder / 'receipt.json', {**config, 'state': 'failed', 'error': str(exc)})
                raise
        config['pid'] = proc.pid
        atomic_json(folder / 'receipt.json', config)
        (folder / 'go').touch()
        return config


def local_json(path, payload=None):
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request('http://127.0.0.1:7332' + path, data=data, headers={'Content-Type': 'application/json'})
    with urllib.request.urlopen(req, timeout=3) as r: return json.load(r)


def write_runtime(path, data, mode):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name('.' + path.name + '.update-' + uuid.uuid4().hex)
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_EXCL, mode)
    with os.fdopen(fd, 'wb') as out: out.write(data)
    os.replace(tmp, path)


def platform_service(action, name):
    linux = {'node': 'future-crash-look-node.service', 'ingress': 'future-crash-look-ingress.service',
             'tailcat': 'future-crash-look-tailcat.service', 'media-watch': 'future-crash-look-media-watch.service', 'signal': 'signal-window.service'}
    mac = {'node': 'com.futurecrash.look.node', 'ingress': 'com.futurecrash.look.ingress',
           'tailcat': 'com.futurecrash.look.tailcat', 'media-watch': 'com.futurecrash.look.media-watch', 'signal': 'com.futurecrash.signal-window'}
    system = platform.system().lower()
    if system == 'linux':
        unit = linux[name]
        if not (Path.home() / '.config/systemd/user' / unit).is_file():
            if name == 'node': raise RuntimeError('node has no managed user service')
            return
        argv = ['systemctl', '--user', 'is-active', '--quiet', unit] if action == 'status' else ['systemctl', '--user', action, unit]
    elif system == 'darwin':
        unit = mac[name]
        if not (Path.home() / 'Library/LaunchAgents' / (unit + '.plist')).is_file():
            if name == 'node': raise RuntimeError('node has no managed user service')
            return
        domain = f'gui/{os.getuid()}/{unit}'
        # KeepAlive agents cannot be reliably stopped with kill; bootout owns retirement.
        if action == 'status': argv = ['launchctl', 'print', domain]
        elif action == 'stop': argv = ['launchctl', 'bootout', domain]
        else:
            plist = str(Path.home() / 'Library/LaunchAgents' / (unit + '.plist'))
            subprocess.run(['launchctl', 'bootstrap', f'gui/{os.getuid()}', plist], capture_output=True, timeout=15)
            argv = ['launchctl', 'kickstart', '-k', domain]
    else: raise RuntimeError('unsupported service platform')
    proc = subprocess.run(argv, capture_output=True, text=True, timeout=20)
    if action == 'status':
        return proc.returncode == 0 and (system != 'darwin' or 'state = running' in proc.stdout)
    if proc.returncode: raise RuntimeError(f'{action} {name}: {proc.stderr.strip()}')


def wait_idle(seconds=300):
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        activity = local_json('/v1/activity')
        media = local_json('/v1/media/state')
        traffic = local_json('/v1/http')
        streaming = any(str(request.get('path', '')).split('?', 1)[0] in {'/v1/media/browser', '/v1/media/audio', '/v1/media/item', '/v1/media/artifact'}
                        for meter in (traffic.get('listeners') or {}).values()
                        for request in meter.get('oldest_active', []))
        if activity.get('active') is None and not media.get('active') and not streaming:
            reserved = local_json('/v1/lease/acquire', {'owner': 'runtime-maintenance', 'priority': 'interactive',
                                   'phase': 'maintenance', 'detail': 'install approved runtime'})
            if reserved.get('lease'): return reserved['lease']['id']
        time.sleep(.5)
    raise TimeoutError('node still busy; finish playback or inference and retry maintenance')


def health(expected=None, seconds=45, services=()):
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        try:
            state = local_json('/health')
            if state.get('ok') and (expected is None or local_json('/v1/maintenance/release').get('digest') == expected) and all(platform_service('status', name) for name in services): return
        except (OSError, ValueError): pass
        time.sleep(.5)
    raise RuntimeError('restarted runtime did not pass health/release verification')


def run_job(job):
    folder = root() / 'jobs' / job
    deadline = time.monotonic() + 5
    while not (folder / 'go').exists():
        if time.monotonic() >= deadline: return
        time.sleep(.05)
    info = receipt(job)
    def phase(state, **fields):
        info.update(state=state, updated=time.time(), pid=os.getpid(), **fields)
        atomic_json(folder / 'receipt.json', info)
    previous = None
    changed = []
    services = ['signal', 'media-watch', 'tailcat', 'ingress', 'node'] if info['action'] == 'update' else ['node']
    retired = []
    modified = False
    lease_id = None
    try:
        manifest = payload = None
        if info['action'] == 'update':
            manifest, payload = validate_bundle((folder / 'release.zip').read_bytes(), info['digest'])
        phase('draining')
        if info['action'] == 'update': lease_id = wait_idle()
        if payload is not None:
            previous = registry().read_bytes()
            backup = folder / 'previous'
            backup.mkdir()
            for f in manifest['files']:
                dst = destination(f['path'])
                saved = backup / f['path']
                if dst.exists():
                    saved.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(dst, saved)
                changed.append((f['path'], dst.exists()))
            atomic_json(folder / 'rollback.json', {'files': changed})
        phase('installing' if payload is not None else 'restarting')
        # Stop imported LOOK code before replacing its module files.
        lk = Path.home() / '.local/bin/lk'
        if lk.exists(): subprocess.run([str(lk), 'ai', 'stop'], capture_output=True, timeout=15)
        # Preserve disabled/stopped optional services rather than starting them as
        # a side effect of updating code. Node itself is always the recovery target.
        services = [name for name in services if name == 'node' or platform_service('status', name)]
        for name in services:
            platform_service('stop', name)
            retired.append(name)
        if payload is not None:
            modified = True
            for f in manifest['files']: write_runtime(destination(f['path']), payload[f['path']], f['mode'])
            atomic_json(registry(), manifest)
        phase('restarting')
        for name in reversed(retired): platform_service('start', name)
        phase('verifying')
        health(info.get('digest'), services=retired)
        if lk.exists(): subprocess.run([str(lk), 'ai', 'start'], capture_output=True, timeout=15)
        phase('healthy', release=(manifest or {}).get('release'), commit=(manifest or {}).get('commit'))
    except Exception as exc:
        phase('rolling_back', error=str(exc))
        recovery_errors = []
        if modified:
            for name in services:
                try: platform_service('stop', name)
                except Exception: pass
            for relative, existed in changed:
                try:
                    dst = destination(relative)
                    saved = folder / 'previous' / relative
                    if existed: write_runtime(dst, saved.read_bytes(), saved.stat().st_mode & 0o777)
                    else: dst.unlink(missing_ok=True)
                except Exception as recovery: recovery_errors.append(str(recovery))
            if previous is not None: write_runtime(registry(), previous, 0o600)
        for name in reversed(retired):
            try: platform_service('start', name)
            except Exception as recovery: recovery_errors.append(str(recovery))
        if retired:
            try: health(services=retired)
            except Exception as recovery: recovery_errors.append(str(recovery))
        if retired and not recovery_errors:
            lk = Path.home() / '.local/bin/lk'
            if lk.exists():
                try: subprocess.run([str(lk), 'ai', 'start'], capture_output=True, timeout=15)
                except Exception as recovery: recovery_errors.append(str(recovery))
        phase('rolled_back' if retired and not recovery_errors else 'failed', recovery_errors=recovery_errors)
    finally:
        if lease_id:
            try: local_json('/v1/lease/release', {'id': lease_id, 'status': 'ok', 'detail': 'maintenance helper finished'})
            except Exception: pass  # A restarted node has already discarded the old lease.


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--register')
    ap.add_argument('--run-job')
    args = ap.parse_args()
    if args.register: register_install(args.register)
    elif args.run_job: run_job(args.run_job)
