"""Paired-node directory browsing and staged, non-overwriting file copies."""
from __future__ import annotations
import os
from pathlib import Path, PurePosixPath
import shutil
import tarfile
import tempfile
import threading

_LOCK = threading.Lock()


def resolve(value):
    raw = str(value)
    if not (raw.startswith('/') or raw == '~' or raw.startswith('~/')):
        raise ValueError('Destination must be an absolute path or ~/ on this node')
    return Path(raw).expanduser().resolve()


def browse(value):
    path = resolve(value)
    if not path.is_dir():
        raise NotADirectoryError(str(path))
    entries = []
    for child in path.iterdir():
        if child.is_dir():
            entries.append({'name': child.name, 'path': str(child)})
    return {'ok': True, 'path': str(path), 'home': str(Path.home()),
            'directories': sorted(entries, key=lambda row: row['name'].casefold())}


def receive(stream, value):
    """Extract regular files into a private stage; publish only after validation.

    Existing destinations are never replaced. Failed batches remove only entries
    created by this operation. Links, devices, and traversal members are refused.
    """
    dest = resolve(value)
    if not dest.is_dir():
        raise NotADirectoryError(f'Choose an existing destination directory: {dest}')
    with _LOCK, tempfile.TemporaryDirectory(prefix='.look-copy-', dir=dest) as folder:
        stage = Path(folder)
        seen = set()
        with tarfile.open(fileobj=stream, mode='r|') as archive:
            for member in archive:
                name = PurePosixPath(member.name)
                if name.is_absolute() or '..' in name.parts or not name.parts or str(name) == '.':
                    raise ValueError('Unsafe archive path')
                if not (member.isfile() or member.isdir()) or str(name) in seen:
                    raise ValueError('Only distinct regular files and directories can be copied')
                seen.add(str(name))
                target = stage.joinpath(*name.parts)
                if member.isdir():
                    target.mkdir(parents=True, exist_ok=True)
                else:
                    target.parent.mkdir(parents=True, exist_ok=True)
                    with archive.extractfile(member) as source, target.open('xb') as output:
                        shutil.copyfileobj(source, output, 1024 * 1024)
                    os.chmod(target, member.mode & 0o777)
                    os.utime(target, (member.mtime, member.mtime))
        items = list(stage.iterdir())
        if not items: raise ValueError('Empty copy archive')
        created = []
        try:
            for item in items:
                target = dest / item.name
                if item.is_dir():
                    target.mkdir()  # exclusive reservation, including empty existing directories
                    created.append(target)
                    for child in item.iterdir():
                        os.rename(child, target / child.name)
                else:
                    os.link(item, target)  # atomic no-clobber publication on the same volume
                    created.append(target)
        except Exception:
            for target in reversed(created):
                if target.is_dir(): shutil.rmtree(target)
                else: target.unlink()
            raise
        return {'ok': True, 'path': str(dest), 'copied': [str(p) for p in created],
                'undo_available': False}
