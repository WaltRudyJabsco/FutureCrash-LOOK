"""Literal Fabric destinations and loopback file transport for LOOK."""
from __future__ import annotations
import json
import re
import tarfile
import tempfile
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path

BASE = 'http://127.0.0.1:7332'


def literal(value):
    value = str(value).strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
        value = value[1:-1]
    return value.replace('\\ ', ' ')


@dataclass(frozen=True)
class Destination:
    node: str
    path: str

    def __str__(self):
        return f'@{self.node}:{self.path}'

    @property
    def name(self):
        return self.path.rstrip('/').rsplit('/', 1)[-1] or self.node

    @property
    def parent(self):
        if self.path == '/':
            return None
        return Destination(self.node, str(Path(self.path.rstrip('/')).parent))


def parse(value):
    raw = literal(value)
    if not raw.startswith('@'):
        return None
    match = re.fullmatch(r'@([^:/\s]+):(.*)', raw)
    if not match:
        raise ValueError('Use @node:/absolute/path or @node:~/path')
    node, path = match.groups()
    if not (path.startswith('/') or path == '~' or path.startswith('~/')):
        raise ValueError('Fabric paths must start with / or ~/ (the destination node home)')
    return Destination(node, path)


def request(route, params=None, data=None, length=None):
    url = BASE + route
    if params:
        url += '?' + urllib.parse.urlencode(params)
    headers = {} if length is None else {'Content-Length': str(length), 'Content-Type': 'application/x-tar'}
    req = urllib.request.Request(url, data=data, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=3600 if data is not None else 8) as response:
            result = json.load(response)
    except urllib.error.HTTPError as exc:
        try: detail = json.load(exc).get('error', str(exc))
        except Exception: detail = str(exc)
        raise RuntimeError(detail) from exc
    if not result.get('ok', True):
        raise RuntimeError(result.get('error') or 'Fabric file operation failed')
    return result


def nodes():
    snapshot = request('/v1/nodes')
    names = set()
    local = (snapshot.get('self') or {}).get('name')
    if local: names.add(local)
    for peer in snapshot.get('peers') or []:
        if not peer.get('node') or not peer.get('trusted'): continue
        name = (peer['node'].get('identity') or {}).get('name') or peer.get('name')
        if name: names.add(name)
    return [Destination(name, '/') for name in sorted(names, key=str.casefold)]


def browse(dest):
    return request('/v1/files/browse', {'target': dest.node, 'path': dest.path})


def copy(paths, destination):
    dest = parse(destination)
    if dest is None: raise ValueError('Fabric destination required')
    paths = [Path(p).absolute() for p in paths]
    if len({p.name for p in paths}) != len(paths):
        raise ValueError('Selected sources have duplicate destination names')
    # A disk-backed archive bounds RAM and includes spaces verbatim, with no shell.
    with tempfile.TemporaryFile() as stream:
        with tarfile.open(fileobj=stream, mode='w') as archive:
            def regular_only(info):
                if not (info.isfile() or info.isdir()):
                    raise ValueError(f'Fabric copy does not follow links or copy special files: {info.name}')
                return info
            for path in paths:
                archive.add(path, arcname=path.name, filter=regular_only)
        length = stream.tell(); stream.seek(0)
        return request('/v1/files/copy', {'target': dest.node, 'path': dest.path}, stream, length)
