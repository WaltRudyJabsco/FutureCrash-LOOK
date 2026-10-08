import io
import json
import tarfile
import threading
import urllib.error
import urllib.request
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import Mock

import pytest
from core import file_transfer, ingress, node
from look import fabric_files as ff, look_renderer as renderer


def archive(entries):
    data = io.BytesIO()
    with tarfile.open(fileobj=data, mode='w') as out:
        for name, body, kind in entries:
            info = tarfile.TarInfo(name)
            info.type = kind
            info.size = len(body) if kind == tarfile.REGTYPE else 0
            info.linkname = '/tmp/escape' if kind == tarfile.SYMTYPE else ''
            out.addfile(info, io.BytesIO(body) if info.isfile() else None)
    data.seek(0)
    return data


def test_literal_remote_paths_and_destination_node_home(tmp_path, monkeypatch):
    monkeypatch.setenv('HOME', str(tmp_path))
    dest = renderer.resolve_action_destination('@3090:~/2TB Storage/', Path('/local'))
    assert str(dest) == '@3090:~/2TB Storage/'
    assert ff.parse('"@3090:/run/media/jreno/2TB Storage/"').path.endswith('2TB Storage/')
    assert ff.parse(r'@3090:/run/media/jreno/2TB\ Storage/').path.endswith('2TB Storage/')
    assert file_transfer.resolve(dest.path) == tmp_path / '2TB Storage'
    for bad in ['@3090/var', '@3090:relative', '@3090:~another/path']:
        with pytest.raises(ValueError): ff.parse(bad)


def test_copy_retains_sources_and_refuses_overwrite_with_rollback(tmp_path):
    target = tmp_path / '2TB Storage'; target.mkdir()
    (target / 'b.mp3').write_bytes(b'original')
    data = archive([('a.mp3', b'new', tarfile.REGTYPE), ('b.mp3', b'bad', tarfile.REGTYPE)])
    with pytest.raises(FileExistsError): file_transfer.receive(data, str(target))
    assert not (target / 'a.mp3').exists()
    assert (target / 'b.mp3').read_bytes() == b'original'
    assert sorted(p.name for p in target.iterdir()) == ['b.mp3']


@pytest.mark.parametrize('name,kind', [('../escape', tarfile.REGTYPE), ('/escape', tarfile.REGTYPE),
                                     ('link', tarfile.SYMTYPE), ('device', tarfile.CHRTYPE)])
def test_unsafe_archive_members_never_publish(tmp_path, name, kind):
    with pytest.raises(ValueError):
        file_transfer.receive(archive([('good', b'ok', tarfile.REGTYPE), (name, b'x', kind)]), str(tmp_path))
    assert list(tmp_path.iterdir()) == []


@contextmanager
def serving(server):
    thread = threading.Thread(target=server.serve_forever, daemon=True); thread.start()
    try: yield f'http://127.0.0.1:{server.server_port}'
    finally: server.shutdown(); server.server_close(); thread.join(2)


def test_large_copy_through_gateway_and_ingress_with_nested_spaces(tmp_path, monkeypatch):
    monkeypatch.setenv('HOME', str(tmp_path))
    monkeypatch.setattr(node, 'identity', lambda: {'name': 'source'})
    monkeypatch.setattr(node.FABRIC_IDENTITY, 'verify_peer', lambda *args: True)
    monkeypatch.setattr(node.FABRIC_IDENTITY, 'auth_headers_for_url', lambda url: {'X-Fabric-Node': 'source', 'Authorization': 'Bearer test'})
    monkeypatch.setattr(node.FABRIC_IDENTITY, 'ssl_context_for_url', lambda url: None)
    monkeypatch.setattr(ingress.FABRIC_IDENTITY, 'verify_peer', lambda *args: True)
    source = tmp_path / 'source' / 'Album With Spaces'; source.mkdir(parents=True)
    content = b'12345678' * (ingress.MAX_BODY_BYTES // 8 + 1)
    (source / 'My Song.mp3').write_bytes(content)
    target = tmp_path / '2TB Storage'; target.mkdir()
    with serving(node.FabricHTTPServer(('127.0.0.1', 0), node.API, plane='ingress')) as backend:
        port = int(backend.rsplit(':', 1)[1])
        with serving(ingress.GuardServer(('127.0.0.1', 0), ingress.Handler, '127.0.0.1', port)) as edge:
            peer = {'name': '3090', 'trusted': True, 'node': {'identity': {'name': '3090'}}, 'url': edge}
            monkeypatch.setattr(node.PEERS, 'public', lambda: [peer])
            # Route probes use the identity endpoint, independently of copying.
            original = node.http_json
            monkeypatch.setattr(node, 'http_json', lambda url, **kw: {'ok': True} if url.endswith('/v1/identity') else original(url, **kw))
            with serving(node.FabricHTTPServer(('127.0.0.1', 0), node.API, plane='local')) as gateway:
                monkeypatch.setattr(ff, 'BASE', gateway)
                listing = ff.browse(ff.Destination('3090', '~/'))
                assert listing['path'] == str(tmp_path)
                assert '2TB Storage' in [row['name'] for row in listing['directories']]
                result = ff.copy([source], '@3090:~/2TB Storage/')
                assert result['ok'] and not result['undo_available']
                assert (target / source.name / 'My Song.mp3').read_bytes() == content
                assert (source / 'My Song.mp3').read_bytes() == content
                with pytest.raises(RuntimeError, match='File exists'):
                    ff.copy([source], '@3090:~/2TB Storage/')
                # A peer cannot use the gateway as a relay to a third node.
                req = urllib.request.Request(gateway + '/v1/files/browse?target=3090&path=/', headers={'X-Fabric-Node': 'peer'})
                with pytest.raises(urllib.error.HTTPError): urllib.request.urlopen(req)


def test_unpaired_file_ingress_is_rejected(monkeypatch):
    monkeypatch.setattr(node.FABRIC_IDENTITY, 'verify_peer', lambda *args: False)
    with serving(node.FabricHTTPServer(('127.0.0.1', 0), node.API, plane='ingress')) as url:
        with pytest.raises(urllib.error.HTTPError) as error:
            urllib.request.urlopen(url + '/v1/files/browse?path=/')
        assert error.value.code == 401


def test_destination_picker_ascends_above_root_and_selects_remote_drive(monkeypatch):
    monkeypatch.setattr(renderer.termios, 'tcgetattr', lambda fd: [])
    monkeypatch.setattr(renderer.termios, 'tcsetattr', lambda *args: None)
    monkeypatch.setattr(renderer.tty, 'setcbreak', lambda fd: None)
    monkeypatch.setattr(renderer.sys, 'stdin', Mock(fileno=lambda: 0))
    monkeypatch.setattr(renderer.sys, 'stdout', io.StringIO())
    monkeypatch.setattr(ff, 'nodes', lambda: [ff.Destination('3090', '/')])
    monkeypatch.setattr(ff, 'browse', lambda dest: {'path': dest.path, 'directories': [{'name': '2TB Storage', 'path': '/run/media/jreno/2TB Storage'}]})
    keys = iter(['\x1b[D', '\x1b[B', '\x1b[C', '\r'])
    monkeypatch.setattr(renderer, 'read_key', lambda: next(keys))
    selected = renderer._destination_picker(Path('/'))
    assert str(selected) == '@3090:/run/media/jreno/2TB Storage'
