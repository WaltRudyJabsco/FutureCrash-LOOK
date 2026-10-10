import io
import json
import os
from pathlib import Path
import uuid
import zipfile
from unittest.mock import Mock

import pytest
from core import maintenance as m
from core import node


RUNTIME = ['.local/share/look/lk', '.local/share/future-crash-look/core/node.py',
           '.local/share/future-crash-look/core/maintenance.py']


def package(files=None, commit='new'):
    files = files or {p: b'# runtime\nvalue = 2\n' for p in RUNTIME}
    manifest = {'protocol': 1, 'release': '8.15.0', 'commit': commit, 'files': [
        {'path': p, 'sha256': m.digest(data), 'size': len(data), 'mode': 0o644}
        for p, data in sorted(files.items())]}
    data = io.BytesIO()
    with zipfile.ZipFile(data, 'w') as z:
        z.writestr('manifest.json', json.dumps(manifest))
        for p, content in files.items(): z.writestr(p, content)
    return data.getvalue(), manifest, files


@pytest.fixture
def home(monkeypatch, tmp_path):
    monkeypatch.setenv('HOME', str(tmp_path))
    return tmp_path


def installed(home):
    raw, manifest, files = package({p: b'# old runtime\nvalue = 1\n' for p in RUNTIME}, commit='old')
    for p, content in files.items(): m.write_runtime(m.destination(p), content, 0o644)
    m.atomic_json(m.registry(), manifest)
    return manifest, files


def staged(home, action='update', raw=None):
    job = uuid.uuid4().hex
    folder = m.root() / 'jobs' / job
    folder.mkdir(parents=True)
    if raw is not None: (folder / 'release.zip').write_bytes(raw)
    m.atomic_json(folder / 'receipt.json', {'job': job, 'action': action, 'state': 'staged', 'digest': m.digest(raw) if raw else None})
    m.atomic_json(m.root() / 'active.json', {'job': job})
    (folder / 'go').touch()
    return job


def test_validated_runtime_bundle_rejects_corruption_traversal_and_syntax(home):
    raw, manifest, files = package()
    assert m.validate_bundle(raw, m.digest(raw))[0]['commit'] == 'new'
    with pytest.raises(ValueError, match='digest'): m.validate_bundle(raw, '0' * 64)
    bad = dict(files, **{'../../.zshrc': b'bad'})
    blob, _, _ = package(bad)
    with pytest.raises(ValueError): m.validate_bundle(blob, m.digest(blob))
    bad = dict(files); bad[RUNTIME[0]] = b'def broken(\n'
    blob, _, _ = package(bad)
    with pytest.raises(ValueError): m.validate_bundle(blob, m.digest(blob))


def test_duplicate_and_unlisted_members_are_rejected(home):
    raw, _, _ = package()
    buf = io.BytesIO(raw)
    with zipfile.ZipFile(buf, 'a') as z: z.writestr('unexpected.json', '{}')
    raw = buf.getvalue()
    with pytest.raises(ValueError, match='inventory'): m.validate_bundle(raw, m.digest(raw))


def test_destination_cannot_follow_symlinks_even_within_home(home):
    redirect = home / 'documents'
    redirect.mkdir()
    base = home / '.local/share/future-crash-look'
    base.mkdir(parents=True)
    (base / 'core').symlink_to(redirect, target_is_directory=True)
    with pytest.raises(ValueError, match='redirect'): m.destination(RUNTIME[1])


def test_update_installs_verifies_and_preserves_user_state(home, monkeypatch):
    installed(home)
    user = home / '.local/share/look/media_library.json'
    user.write_text('user-owned catalog')
    raw, manifest, files = package()
    job = staged(home, raw=raw)
    services = []
    monkeypatch.setattr(m, 'wait_idle', lambda: None)
    monkeypatch.setattr(m, 'platform_service', lambda action, name: services.append((action, name)))
    def verify(expected, **kwargs):
        assert all(m.destination(p).read_bytes() == content for p, content in files.items())
        assert json.loads(m.registry().read_text()) == manifest
        assert m.draining()
    monkeypatch.setattr(m, 'health', verify)
    m.run_job(job)
    assert m.receipt(job)['state'] == 'healthy'
    assert services.index(('stop', 'node')) < services.index(('start', 'node'))
    assert user.read_text() == 'user-owned catalog'
    assert not m.draining()


def test_failed_health_restores_old_files_and_removes_added_modules(home, monkeypatch):
    old, old_files = installed(home)
    files = {p: b'new = True\n' for p in RUNTIME}
    added = '.local/share/look/new_module.py'
    files[added] = b'new = True\n'
    raw, _, _ = package(files)
    job = staged(home, raw=raw)
    monkeypatch.setattr(m, 'wait_idle', lambda: None)
    monkeypatch.setattr(m, 'platform_service', lambda *a: None)
    def health(expected=None, **kwargs):
        if expected: raise RuntimeError('new runtime unhealthy')
        assert json.loads(m.registry().read_text()) == old
    monkeypatch.setattr(m, 'health', health)
    m.run_job(job)
    assert m.receipt(job)['state'] == 'rolled_back'
    assert all(m.destination(p).read_bytes() == content for p, content in old_files.items())
    assert not m.destination(added).exists()


def test_update_timeout_does_not_touch_or_restart_runtime(home, monkeypatch):
    installed(home)
    raw, _, _ = package()
    job = staged(home, raw=raw)
    monkeypatch.setattr(m, 'wait_idle', Mock(side_effect=TimeoutError('still busy')))
    restart = Mock()
    monkeypatch.setattr(m, 'platform_service', restart)
    m.run_job(job)
    restart.assert_not_called()
    assert m.receipt(job)['state'] == 'failed'
    assert json.loads(m.registry().read_text())['commit'] == 'old'


def test_explicit_restart_can_recover_busy_worker_without_updating_files(home, monkeypatch):
    installed(home)
    job = staged(home, action='restart')
    wait = Mock(side_effect=AssertionError('must not wait for ghost busy lease'))
    monkeypatch.setattr(m, 'wait_idle', wait)
    actions = []
    monkeypatch.setattr(m, 'platform_service', lambda *a: actions.append(a))
    monkeypatch.setattr(m, 'health', lambda expected=None, **kwargs: None)
    m.run_job(job)
    assert actions == [('stop', 'node'), ('start', 'node')]
    assert m.receipt(job)['state'] == 'healthy'
    assert json.loads(m.registry().read_text())['commit'] == 'old'


def test_bundle_is_stable_and_modified_code_is_not_distributed(home):
    installed(home)
    first = m.bundle()[1]
    assert first == m.bundle()[1]
    m.destination(RUNTIME[0]).write_text('modified')
    assert not m.release_info()['available']


def test_schedule_detaches_pinned_runner_and_blocks_duplicate_job(home, monkeypatch):
    installed(home)
    proc = Mock(pid=os.getpid())
    launch = Mock(return_value=proc)
    monkeypatch.setattr(m.subprocess, 'Popen', launch)
    result = m.schedule('restart')
    folder = m.root() / 'jobs' / result['job']
    assert (folder / 'runner.py').read_bytes() == Path(m.__file__).read_bytes()
    assert (folder / 'go').exists()
    assert launch.call_args.kwargs['start_new_session']
    with pytest.raises(ValueError, match='already in progress'): m.schedule('restart')


def test_receiver_requires_explicit_approved_digest_before_network(monkeypatch):
    opener = Mock()
    monkeypatch.setattr(node.urllib.request, 'urlopen', opener)
    with pytest.raises(PermissionError): node._maintenance_update({'confirm': False})
    with pytest.raises(ValueError): node._maintenance_update({'confirm': True, 'digest': 'wrong'})
    opener.assert_not_called()


def test_manual_install_registers_only_code_not_catalogs(home, monkeypatch, tmp_path):
    source = tmp_path / 'checkout'
    for p in ['core/node.py', 'core/maintenance.py', 'look/lk', 'look/lo_history.py']:
        src = source / p; src.parent.mkdir(parents=True, exist_ok=True); src.write_text('# code\n')
        target = ('.local/share/look/' + src.name) if p.startswith('look/') else '.local/share/future-crash-look/core/' + src.name
        m.write_runtime(m.destination(target), src.read_bytes(), 0o644)
    (source / 'VERSION').write_text('8.15.0')
    m.write_runtime(m.destination('.local/share/future-crash-look/RELEASE'), b'8.15.0', 0o644)
    (home / '.local/share/look/lo_history.json').write_text('["private prompt"]')
    monkeypatch.setattr(m.subprocess, 'run', Mock(side_effect=FileNotFoundError('git missing')))
    result = m.register_install(source)
    assert result['commit'] is None
    assert all('history.json' not in f['path'] for f in result['files'])


def test_idle_update_reserves_worker_and_respects_active_media_stream(home, monkeypatch):
    rounds = []
    stream = {'listeners': {'tailcat': {'oldest_active': [{'path': '/v1/media/browser'}]}}}
    def local(path, payload=None):
        rounds.append(path)
        if path == '/v1/activity': return {'active': None}
        if path == '/v1/media/state': return {'active': False}
        if path == '/v1/http':
            return stream if rounds.count(path) == 1 else {'listeners': {}}
        assert path == '/v1/lease/acquire'
        assert payload['priority'] == 'interactive'
        return {'lease': {'id': 'reserved'}}
    monkeypatch.setattr(m, 'local_json', local)
    monkeypatch.setattr(m.time, 'sleep', lambda s: None)
    assert m.wait_idle(1) == 'reserved'
    assert rounds.count('/v1/http') == 2
    assert rounds.count('/v1/lease/acquire') == 1


def test_linux_service_status_and_restart_use_user_units(home, monkeypatch):
    unit = home / '.config/systemd/user/future-crash-look-node.service'
    unit.parent.mkdir(parents=True); unit.touch()
    monkeypatch.setattr(m.platform, 'system', lambda: 'Linux')
    run = Mock(return_value=Mock(returncode=0, stdout='', stderr=''))
    monkeypatch.setattr(m.subprocess, 'run', run)
    assert m.platform_service('status', 'node')
    assert run.call_args.args[0] == ['systemctl', '--user', 'is-active', '--quiet', unit.name]
    m.platform_service('start', 'node')
    assert run.call_args.args[0] == ['systemctl', '--user', 'start', unit.name]


def test_mac_service_restart_bootstraps_before_kickstart(home, monkeypatch):
    unit = home / 'Library/LaunchAgents/com.futurecrash.look.node.plist'
    unit.parent.mkdir(parents=True); unit.touch()
    monkeypatch.setattr(m.platform, 'system', lambda: 'Darwin')
    run = Mock(return_value=Mock(returncode=0, stdout='state = running', stderr=''))
    monkeypatch.setattr(m.subprocess, 'run', run)
    m.platform_service('start', 'node')
    assert run.call_args_list[0].args[0][:2] == ['launchctl', 'bootstrap']
    assert run.call_args_list[1].args[0][:3] == ['launchctl', 'kickstart', '-k']
    assert m.platform_service('status', 'node')


def test_cli_update_names_source_and_sends_only_explicit_targets(monkeypatch, capsys):
    monkeypatch.setattr(node.sys, 'argv', ['fcl-node', 'update', 'm3', '3090', '--yes'])
    monkeypatch.setattr(node, '_daemon_get', lambda *a: {'self': {'name': 'm3'}, 'peers': []})
    monkeypatch.setattr(node, '_target_get', lambda *a: {'available': True, 'digest': 'a' * 64, 'commit': 'exact-commit'})
    post = Mock(return_value={'ok': True, 'job': 'job-id', 'state': 'staged'})
    monkeypatch.setattr(node, '_target_post', post)
    assert node.main() == 0
    assert post.call_args.args[2:4] == ('3090', '/v1/maintenance/update')
    assert post.call_args.args[4] == {'source': 'm3', 'digest': 'a' * 64, 'confirm': True}
    assert 'exact-commit' in capsys.readouterr().out


def test_cli_receipt_accepts_remote_node_and_job_id(monkeypatch):
    job = 'a' * 32
    monkeypatch.setattr(node.sys, 'argv', ['fcl-node', 'maintenance', '--node', '3090', job])
    get = Mock(return_value={'state': 'healthy'})
    monkeypatch.setattr(node, '_target_get', get)
    assert node.main() == 0
    assert get.call_args.args[2:] == ('3090', '/v1/maintenance/status?job=' + job)


def test_unpaired_ingress_cannot_read_release_or_trigger_update(monkeypatch):
    handler = Mock()
    handler.server.plane = 'edge'
    handler.headers = {}
    monkeypatch.setattr(node.FABRIC_IDENTITY, 'verify_peer', lambda *a: False)
    for path in ('/v1/maintenance/release', '/v1/maintenance/bundle', '/v1/maintenance/update'):
        assert node.API._authorized_ingress(handler, path) is False
    assert all(call.args[0] == 401 for call in handler.sendj.call_args_list)


def test_release_digest_survives_manifest_roundtrip_and_local_file_modes(home):
    installed(home)
    original = m.bundle()[1]
    manifest, payload = m.validate_bundle(original, m.digest(original))
    for f in manifest['files']:
        m.write_runtime(m.destination(f['path']), payload[f['path']], 0o755)
    m.atomic_json(m.registry(), manifest)
    assert m.release_info()['digest'] == m.digest(original)


def test_receiver_resolves_source_with_real_peer_registry_and_stages(home, monkeypatch):
    installed(home)
    data, _, _ = package()
    expected = m.digest(data)
    # Keep the actual PeerRegistry.public method: inventing a snapshot stub hid
    # an AttributeError in the receive path before the first real deployment.
    monkeypatch.setattr(node.PEERS, 'rows', [{'name': '3090', 'node': {'identity': {'name': '3090'}},
                                           'url': 'https://3090.example:7443'}])
    monkeypatch.setattr(node, 'advertisement', lambda: {})
    monkeypatch.setattr(node, 'identity', lambda: {'name': 'm3max-pro'})
    monkeypatch.setattr(node.maintenance, 'release_info', lambda: {'digest': 'old'})
    monkeypatch.setattr(node.FABRIC_IDENTITY, 'auth_headers_for_url', lambda url: {'Authorization': 'paired'})
    monkeypatch.setattr(node.FABRIC_IDENTITY, 'ssl_context_for_url', lambda url: None)
    opener = Mock(return_value=io.BytesIO(data))
    monkeypatch.setattr(node.urllib.request, 'urlopen', opener)
    stage = Mock(return_value={'job': 'a' * 32, 'state': 'staged'})
    monkeypatch.setattr(node.maintenance, 'schedule', stage)
    result = node._maintenance_update({'source': '3090', 'digest': expected, 'confirm': True})
    assert result['ok'] and result['state'] == 'staged'
    assert opener.call_args.args[0].full_url == 'https://3090.example:7443/v1/maintenance/bundle'
    stage.assert_called_once_with('update', data=data, expected=expected)
