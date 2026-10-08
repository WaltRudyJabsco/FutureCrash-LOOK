"""Bounded, node-qualified history for LOOK destination discovery."""
from __future__ import annotations
import json, os, time, uuid
from pathlib import Path
try:
    from . import fabric_files
except ImportError:
    import fabric_files


def location(): return Path.home()/'.local/share/look/destination_history.json'


def recent(node=None):
    try: rows=json.loads(location().read_text())
    except (OSError,ValueError): return []
    if not isinstance(rows,list): return []
    rows=[row for row in rows if isinstance(row,dict) and isinstance(row.get('value'),str)]
    result=[]
    for row in rows:
        try: dest=fabric_files.parse(row['value'])
        except ValueError: continue
        if node is not None and (dest is None or dest.node.casefold()!=node.casefold()): continue
        if node is None and dest is not None: continue
        if dest is None and not Path(row['value']).is_absolute(): continue
        result.append(row)
    return result[:32]


def remember(value):
    value=str(value); remote=fabric_files.parse(value)
    if remote is None: value=str(Path(value).expanduser().resolve())
    rows=[]
    # Retain history from all nodes; recent(None) intentionally displays only local paths.
    try: old=json.loads(location().read_text())
    except (OSError,ValueError): old=[]
    if isinstance(old,list): rows=[row for row in old if isinstance(row,dict) and isinstance(row.get('value'),str) and row['value']!=value]
    rows=[{'value':value,'used':time.time()},*rows][:64]
    path=location(); path.parent.mkdir(parents=True,exist_ok=True)
    temporary=path.with_name(path.name+'.'+uuid.uuid4().hex+'.tmp')
    try:
        temporary.write_text(json.dumps(rows)); temporary.chmod(0o600); temporary.replace(path)
    finally: temporary.unlink(missing_ok=True)
