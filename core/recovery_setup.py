"""Drive discovery and guided recovery setup; all choices belong to this user."""
from __future__ import annotations
import json
import os
from pathlib import Path
import plistlib
import re
import shutil
import subprocess
import sys
import urllib.request

CHECK_SECONDS = 3600
SERVICE = 'future-crash-look-recovery'
MAC_LABEL = 'com.futurecrash.look.recovery'


def engine():
    try:
        from . import recovery
    except ImportError:
        import recovery
    return recovery


def clean(value):
    return ''.join(c for c in str(value) if c.isprintable())


def command(argv, *, binary=False):
    result = subprocess.run(argv, capture_output=True, text=not binary, timeout=20)
    if result.returncode:
        raise RuntimeError('Could not inspect drives: ' + clean(result.stderr.decode(errors='replace') if binary else result.stderr))
    return result.stdout


def mounted_drives(*, external_only=True):
    """Report volumes, not disk names; UUIDs survive mount-point changes."""
    rows = []
    if sys.platform == 'darwin':
        data = plistlib.loads(command(['/usr/sbin/diskutil', 'list', '-plist'], binary=True))
        for device in data.get('AllDisks', []):
            info = plistlib.loads(command(['/usr/sbin/diskutil', 'info', '-plist', device], binary=True))
            mount = info.get('MountPoint'); uuid = info.get('VolumeUUID')
            if not mount or not uuid or mount == '/' or mount.startswith(('/System/', '/Library/')): continue
            if info.get('ReadOnlyVolume') or info.get('ReadOnlyMedia') or not info.get('WritableVolume', True) or not info.get('WritableMedia', True): continue
            if info.get('BusProtocol') == 'Disk Image' or info.get('SystemImage') or info.get('Locked'): continue
            if external_only and info.get('Internal', True): continue
            rows.append({'uuid': uuid, 'mount': mount, 'name': info.get('VolumeName') or device,
                         'filesystem': info.get('FilesystemType') or info.get('FilesystemName', ''), 'device': device})
    elif sys.platform.startswith('linux'):
        data = json.loads(command(['lsblk', '--json', '--bytes', '--output', 'NAME,PATH,TYPE,LABEL,UUID,FSTYPE,MOUNTPOINTS,RO,RM,TRAN']))
        def visit(devices, external=False):
            for d in devices:
                attached = external or d.get('tran') == 'usb' or bool(d.get('rm'))
                for mount in d.get('mountpoints') or []:
                    if not mount or not d.get('uuid') or d.get('ro') or mount == '/' or mount.startswith(('/boot', '/snap/', '/sys/', '/proc/', '/dev/')): continue
                    if external_only and not attached: continue
                    rows.append({'uuid': d['uuid'], 'mount': mount, 'name': d.get('label') or d['name'],
                                 'filesystem': d.get('fstype') or '', 'device': d.get('path') or d['name']})
                visit(d.get('children') or [], attached)
        visit(data.get('blockdevices') or [])
    else:
        raise ValueError('Backup drive setup supports macOS and Linux')
    result = []
    for row in rows:
        path = Path(row['mount'])
        if not path.is_mount(): continue
        try:
            if os.statvfs(path).f_flag & os.ST_RDONLY: continue
        except OSError: continue
        usage = shutil.disk_usage(path)
        result.append({**row, 'bytes': usage.total, 'free_bytes': usage.free})
    return sorted(result, key=lambda row: (row['name'].casefold(), row['mount']))


def ssh_target(value):
    if not re.fullmatch(r'[A-Za-z0-9_][A-Za-z0-9_.-]*@[A-Za-z0-9][A-Za-z0-9.-]*', value or ''):
        raise ValueError('Use USER@HOST; choose the remote account that owns its Fabric state')
    return value


def ssh_options():
    options = ['-o', 'BatchMode=yes', '-o', 'StrictHostKeyChecking=yes', '-o', 'ConnectTimeout=10',
               '-o', 'ServerAliveInterval=15', '-o', 'ServerAliveCountMax=2']
    if sys.platform == 'darwin': options += ['-o', 'UseKeychain=yes']
    return options


def check_source(target):
    target = ssh_target(target)
    result = subprocess.run(['ssh', *ssh_options(), target, '~/.local/bin/fcl-recovery inventory'], capture_output=True, text=True, timeout=30)
    if result.returncode:
        raise ValueError(f'{target}: SSH access is not ready. Enable Remote Login/SSH and establish a verified SSH key login for that account before adding it. ' + clean(result.stderr[-300:]))
    value = json.loads(result.stdout)
    if 'files' not in value or value.get('ok') is False: raise ValueError(target + ': install the current Fabric recovery helper first')
    return value


def peer_choices():
    """Discovery suggests only trusted peers; it never imports somebody's accounts."""
    try:
        with urllib.request.urlopen('http://127.0.0.1:7332/v1/nodes', timeout=5) as response: data = json.load(response)
    except (OSError, ValueError): return []
    return [{'name': p.get('name') or p.get('dns'), 'host': p.get('dns')}
            for p in data.get('peers', []) if p.get('trusted') and p.get('dns')]


def copy_key(home, destination):
    r = engine(); original = r.root(home) / 'key'
    destination = Path(destination).expanduser().absolute()
    if destination.is_symlink() or destination.exists(): raise ValueError('Recovery-key copy needs a new file')
    destination = destination.parent.resolve() / destination.name
    repo = r.checked_repository(home)
    if repo is None: raise ValueError('Connect the backup drive before saving its recovery key')
    mount = repo.parent.parent.resolve()
    if destination.is_relative_to(mount): raise ValueError('Keep the spare key away from the backup drive')
    if destination == original.resolve(): raise ValueError('Choose a separate recovery-key file')
    if original.is_symlink() or original.stat().st_mode & 0o077: raise ValueError('Recovery key must be private')
    fd = os.open(destination, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(fd, 'wb') as out: out.write(original.read_bytes())
        if destination.stat().st_mode & 0o077: raise ValueError('Choose a filesystem that supports a private recovery-key file')
    except BaseException:
        destination.unlink(); raise
    return str(destination)


def schedule(home, enabled):
    """Generate user-local jobs; no usernames, node names or drive IDs in templates."""
    home = Path(home); exe = str(home / '.local/bin/fcl-recovery')
    logs = home / '.local/share/future-crash-look'; logs.mkdir(parents=True, exist_ok=True)
    if sys.platform == 'darwin':
        folder = home / 'Library/LaunchAgents'; folder.mkdir(parents=True, exist_ok=True)
        path = folder / (MAC_LABEL + '.plist')
        if path.is_symlink(): raise ValueError('Backup schedule must not redirect elsewhere')
        domain = f'gui/{os.getuid()}'
        if path.exists():
            result = subprocess.run(['launchctl', 'bootout', domain + '/' + MAC_LABEL], capture_output=True, text=True, timeout=20)
            if result.returncode and 'No such process' not in result.stderr and 'Could not find service' not in result.stderr:
                raise RuntimeError('Could not stop backup schedule: ' + clean(result.stderr))
        if not enabled:
            path.unlink(missing_ok=True); return
        value = {'Label': MAC_LABEL, 'ProgramArguments': [exe, 'scheduled'], 'StartInterval': CHECK_SECONDS,
                 'RunAtLoad': True, 'Umask': 0o077, 'StandardOutPath': str(logs / 'recovery.log'),
                 'StandardErrorPath': str(logs / 'recovery.log')}
        path.write_bytes(plistlib.dumps(value)); path.chmod(0o600)
        argv = ['launchctl', 'bootstrap', domain, str(path)]
    elif sys.platform.startswith('linux'):
        folder = home / '.config/systemd/user'; folder.mkdir(parents=True, exist_ok=True)
        if any((folder / (SERVICE + suffix)).is_symlink() for suffix in ('.timer','.service')):
            raise ValueError('Backup schedule must not redirect elsewhere')
        if not enabled:
            if not (folder / (SERVICE + '.timer')).exists(): return
            argv = ['systemctl', '--user', 'disable', '--now', SERVICE + '.timer']
        else:
            quoted = exe.replace('\\', '\\\\').replace('"', '\\"').replace('%', '%%')
            (folder / (SERVICE + '.service')).write_text('[Unit]\nDescription=Verified Fabric recovery\n[Service]\nType=oneshot\nUMask=0077\nExecStart="' + quoted + '" scheduled\nNice=10\n')
            (folder / (SERVICE + '.timer')).write_text('[Unit]\nDescription=Check daily Fabric recovery when connected\n[Timer]\nOnBootSec=5min\nOnUnitActiveSec=1h\nRandomizedDelaySec=5min\n[Install]\nWantedBy=timers.target\n')
            result = subprocess.run(['systemctl', '--user', 'daemon-reload'], capture_output=True, text=True, timeout=20)
            if result.returncode: raise RuntimeError('Could not reload backup schedule: ' + clean(result.stderr))
            argv = ['systemctl', '--user', 'enable', '--now', SERVICE + '.timer']
    else: raise ValueError('Schedules support macOS and Linux')
    result = subprocess.run(argv, capture_output=True, text=True, timeout=20)
    if result.returncode: raise RuntimeError('Could not configure backup schedule: ' + clean(result.stderr))


def collect_local(home, source, due=False):
    r = engine(); source = ssh_target(source)
    receipt_path = r.root(home) / ('collected-' + r.hashlib.sha256(source.encode()).hexdigest()[:16] + '.json')
    if due and receipt_path.exists():
        receipt = json.loads(receipt_path.read_text())
        if r.time.time() - receipt.get('verified_at', 0) < r.DAILY_SECONDS: return {'skipped': 'daily recovery already verified'}
    # Stderr uses a file so a remote failure cannot fill a pipe and deadlock receipt reading.
    with r.tempfile.TemporaryFile() as errors:
        origin = subprocess.Popen(['ssh', *ssh_options(), source, '~/.local/bin/fcl-recovery stream'], stdout=subprocess.PIPE, stderr=errors)
        try:
            receipt = r.receive(home, origin.stdout)
            origin.stdout.close(); code = origin.wait(timeout=30)
            if code:
                errors.seek(0); raise RuntimeError('Recovery collection failed: ' + clean(errors.read(1500).decode(errors='replace')))
            if not receipt.get('restore_tested'): raise ValueError('Recovery restore was not verified')
            r.private_json(receipt_path, {**receipt, 'source': source, 'destination': 'local'})
            return receipt
        finally:
            if origin.stdout: origin.stdout.close()
            if origin.poll() is None: origin.kill(); origin.wait()


def run_configured(home, *, due=True):
    r = engine(); plan_path = r.root(home) / 'setup.json'
    if not plan_path.exists(): raise ValueError('Use lk fabric backup add to configure recovery')
    plan = json.loads(plan_path.read_text())
    if due and not plan.get('ready'): return {'skipped': 'setup needs a successful verification; run lk fabric backup configure'}
    if r.checked_repository(home) is None: return {'skipped': 'backup drive disconnected'}
    results = []; errors = []
    for source in [None, *plan.get('sources', [])]:
        try: results.append({'source': source or 'this computer', **(collect_local(home, source, due) if source else r.backup(home, due=due))})
        except (OSError, ValueError, RuntimeError, subprocess.SubprocessError, r.tarfile.TarError, r.sqlite3.Error) as exc:
            errors.append({'source': source or 'this computer', 'error': clean(exc)})
    return {'verified': not errors, 'results': results, 'errors': errors}


def configure(home, *, mount=None, key_copy=None, sources=(), daily=True):
    r = engine(); home = Path(home)
    if not shutil.which('restic'): raise ValueError('Install Restic first: brew install restic (Mac), or sudo apt install restic (Ubuntu)')
    sources = list(dict.fromkeys(ssh_target(s) for s in sources))
    for source in sources: check_source(source)
    existing = (r.root(home) / 'destination.json').exists()
    if not existing:
        choices = [d for d in mounted_drives() if Path(d['mount']).resolve() == Path(mount or '').expanduser().resolve()]
        if len(choices) != 1: raise ValueError('Select a connected external drive from lk fabric backup drives')
        if not key_copy: raise ValueError('Choose where to save a spare recovery key with --key-copy')
        spare = Path(key_copy).expanduser().absolute()
        if spare.exists() or spare.is_symlink() or not spare.parent.is_dir(): raise ValueError('Spare recovery key needs a new file in an existing folder')
        if (spare.parent.resolve() / spare.name).is_relative_to(Path(choices[0]['mount']).resolve()): raise ValueError('Save the spare key away from the backup drive')
        r.initialize(home, choices[0]['uuid'])
        config = r.load_config(home)
        config['name'] = clean(choices[0].get('name') or Path(choices[0]['mount']).name)
        r.private_json(r.root(home) / 'destination.json', config)
        r.private_json(r.root(home) / 'setup.json', {'schema':1, 'ready':False, 'sources':[], 'schedule':'manual', 'key_copy':None})
    elif mount:
        configured = r.checked_repository(home)
        if configured is None or configured.parent.parent.resolve() != Path(mount).expanduser().resolve():
            raise ValueError('This account already has a different destination; it will not be replaced')
    old_plan = r.root(home) / 'setup.json'
    prior = json.loads(old_plan.read_text()) if old_plan.exists() else {}
    if existing and old_plan.exists() and not prior.get('key_copy') and not key_copy:
        raise ValueError('Setup needs a spare recovery key; use configure --yes --key-copy NEW_FILE')
    key_path = copy_key(home, key_copy) if key_copy else prior.get('key_copy')
    plan = {'schema': 1, 'sources': sources, 'schedule': 'daily' if daily else 'manual', 'key_copy': key_path, 'ready': False}
    r.private_json(r.root(home) / 'setup.json', plan)
    report = run_configured(home, due=False)
    if not report.get('verified') or not report.get('results') or not all(row.get('restore_tested') for row in report['results']):
        report['verified'] = False
        if not report.get('errors'): report['errors'] = [{'source':'setup', 'error': report.get('skipped') or 'First backup was skipped; finish it before enabling a schedule'}]
        return {**report, 'configured': True, 'scheduled': False, 'next': 'Fix the reported source, then run lk fabric backup configure'}
    schedule(home, daily)
    plan['ready'] = True
    r.private_json(r.root(home) / 'setup.json', plan)
    return {**report, 'configured': True, 'scheduled': daily, 'key_copy': key_path}


def show_status(home):
    r = engine(); value = r.status(home)
    print('FABRIC BACKUP')
    print('Protects Fabric identity, Notes and settings. Documents, photos and media are not included.')
    if value['role'] == 'destination owner':
        config = r.load_config(home)
        print('Drive: ' + clean(config.get('name') or 'Recovery drive') + ' · ' + ('connected' if value['connected'] else 'disconnected') + ' · UUID ' + value['uuid'])
        receipt = value.get('last_backup')
        print('Last local restore test: ' + (r.time.strftime('%Y-%m-%d %H:%M', r.time.localtime(receipt['verified_at'])) if receipt else 'not yet verified'))
        path = r.root(home) / 'setup.json'
        plan = json.loads(path.read_text()) if path.exists() else None
        print('Schedule: ' + ((plan.get('schedule', 'manual') if plan.get('ready') else 'setup incomplete; run configure') if plan else 'legacy setup; use configure to manage it'))
        for source in (plan or {}).get('sources', []): print('  Contributor: ' + clean(source))
        for receipt in value.get('received', []): print('  Verified: ' + clean(receipt.get('label') or receipt['node']))
    else:
        print('No drive configured here.' if value['role'] == 'unconfigured' else 'This computer contributes to another backup owner.')
        print('Connect an external drive, then choose Add backup drive or run lk fabric backup add.')
    print('Recovery keys stay private to this account. Keep a spare key separately; it is required for recovery.')
    return value


def wizard(home, *, updating=False):
    r = engine(); print('FABRIC BACKUP SETUP')
    print('This saves encrypted Fabric identity, Notes and settings, with a real restore test.')
    print('Documents, photos and media are not included. Other drive files stay untouched.')
    if not shutil.which('restic'): raise ValueError('Install Restic first: brew install restic (Mac), or sudo apt install restic (Ubuntu). Then return here.')
    existing = (r.root(home) / 'destination.json').exists()
    if existing and not updating:
        show_status(home); print('A drive is already configured. Choose Configure to change contributors or schedule.'); return {'already_configured': True}
    mount = None; key = None
    if not existing:
        drives = mounted_drives()
        if not drives: raise ValueError('No writable external drive is mounted. Connect/unlock one in Finder or your file manager, then try again.')
        for i, drive in enumerate(drives, 1):
            print(f"  {i}. {clean(drive['name'])} · {drive['bytes']/1024**3:.0f} GiB · {drive['free_bytes']/1024**3:.0f} GiB free · {clean(drive['mount'])}")
        choice = input('Drive number (Enter cancels): ').strip()
        if not choice: return {'cancelled': True}
        if not choice.isdigit() or not 1 <= int(choice) <= len(drives): raise ValueError('Choose a listed drive number')
        mount = drives[int(choice)-1]['mount']
        key = input('Save spare recovery key to a NEW file outside that drive (Enter cancels): ').strip()
        if not key: return {'cancelled': True}
    elif (r.root(home) / 'setup.json').exists() and not json.loads((r.root(home) / 'setup.json').read_text()).get('key_copy'):
        key = input('Save spare recovery key to a NEW file outside the drive (Enter cancels): ').strip()
        if not key: return {'cancelled': True}
    peers = peer_choices(); sources = []
    print('This computer is included. Add only accounts whose Fabric state you want to protect.')
    for i, peer in enumerate(peers, 1): print(f"  {i}. {clean(peer['name'])} · {clean(peer['host'])}")
    selected = input('Other node numbers, separated by spaces (Enter: this computer only): ').split()
    for number in selected:
        if not number.isdigit() or not 1 <= int(number) <= len(peers): raise ValueError('Choose listed node numbers')
        peer = peers[int(number)-1]
        username = input('SSH account on ' + clean(peer['name']) + ' (Enter cancels): ').strip()
        if not username: return {'cancelled': True}
        sources.append(ssh_target(username + '@' + peer['host']))
    answer = input('Daily backup while connected? [Y/n]: ').strip().lower()
    if answer not in {'', 'y', 'yes', 'n', 'no'}: raise ValueError('Choose yes or no')
    daily = answer not in {'n', 'no'}
    print('Destination: ' + (clean(mount) if mount else 'existing drive'))
    print('Includes: this computer' + ''.join(', ' + clean(s) for s in sources))
    print('Schedule: ' + ('daily, checked hourly' if daily else 'manual'))
    if input('Create/update this backup and verify it now? [y/N]: ').strip().lower() not in {'y', 'yes'}: return {'cancelled': True}
    print('Creating encrypted backup and checking a real restore…', flush=True)
    return configure(home, mount=mount, key_copy=key, sources=sources, daily=daily)


def menu(home):
    while True:
        show_status(home)
        print('  1. Add backup drive\n  2. Configure contributors / schedule\n  3. Back up now\n  4. What is protected?\n  5. Recovery instructions\n  Enter. Back')
        choice = input('Choose: ').strip()
        if not choice: return
        try:
            if choice in {'1', '2'}: report(wizard(home, updating=choice == '2'))
            elif choice == '3': report(run_configured(home, due=False) if (engine().root(home)/'setup.json').exists() else engine().backup(home))
            elif choice == '4':
                value = engine().inventory(home); print(f"{value['files']} files · {value['bytes']/1024**2:.1f} MiB")
                for item in value['excluded']: print('  Excludes: ' + item)
            elif choice == '5': print('Keep the spare key away from the backup drive. Restore into a NEW directory with lk fabric backup restore DIR. This checks recovered data; it does not activate an identity or overwrite your running Fabric.')
            else: print('Choose a listed number.')
        except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as exc: print('BACKUP · ' + clean(exc))
        input('Enter to return: ')


def report(value):
    if value.get('restore_tested'): print(clean(value.get('label') or value.get('node') or 'This computer') + ' · restore verified')
    if value.get('cancelled'): print('Setup cancelled; no backup was configured.'); return
    for row in value.get('results', []):
        print(clean(row['source']) + ' · ' + ('restore verified' if row.get('restore_tested') else clean(row.get('skipped', 'not verified'))))
    for error in value.get('errors', []): print(clean(error['source']) + ' · ' + clean(error['error']))
    if value.get('configured'): print('Backup configured · ' + ('daily schedule enabled' if value.get('scheduled') else 'manual / schedule not enabled'))
    if value.get('key_copy'): print('Spare recovery key saved: ' + value['key_copy'])
    if value.get('skipped'): print(clean(value['skipped']))
    if value.get('next'): print(value['next'])
