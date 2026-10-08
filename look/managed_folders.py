"""Discovery roots owned by LOOK; original files remain untouched."""
from __future__ import annotations
import json, uuid
from pathlib import Path


def registry(): return Path.home()/'.local/share/look/managed_folders.json'


def roots():
    home=Path.home(); result={home/'Downloads/LOOK',home/'Downloads/LOOK-Holding',home/'Pictures/LOOK'}
    try:
        saved=json.loads(registry().read_text())
        if isinstance(saved,list): result.update(Path(value) for value in saved if isinstance(value,str) and Path(value).is_absolute())
    except (OSError,ValueError): pass
    return sorted((path for path in result if path!=path.parent),key=str)


def register(folder):
    folder=Path(folder).expanduser().resolve()
    if folder==folder.parent: return
    values={str(path) for path in roots()}; values.add(str(folder))
    path=registry(); path.parent.mkdir(parents=True,exist_ok=True)
    temporary=path.with_name(path.name+'.'+uuid.uuid4().hex+'.tmp')
    try:
        temporary.write_text(json.dumps(sorted(values))); temporary.chmod(0o600); temporary.replace(path)
    finally: temporary.unlink(missing_ok=True)


def refresh_catalog():
    try: from . import file_catalog
    except ImportError: import file_catalog
    receipts=[]
    for root in roots():
        if root.is_dir(): receipts.append(file_catalog.scan(Path.home()/'.local/share/look/file_catalog.sqlite3',root,default_home=True))
    return receipts
