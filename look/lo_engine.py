#!/usr/bin/env python3
"""In-process machine interface to LO.

This is the reusable edge for browser/native clients.  It deliberately invokes
LOOK's mature LO engine directly instead of spawning the human terminal CLI.
"""
from __future__ import annotations

import contextlib
import importlib.machinery
import importlib.util
import io
import os
import re
import shlex
import sys
import threading
from pathlib import Path

_CORE = None
_CORE_LOCK = threading.Lock()
_CHAT_LOCK = threading.Lock()


def _lk_path() -> Path:
    candidates = [
        Path.home()/'.local/share/look/lk',
        Path(__file__).resolve().with_name('lk'),
    ]
    for path in candidates:
        if path.is_file():
            return path
    raise RuntimeError('LOOK core is not installed')


def _load_core():
    global _CORE
    with _CORE_LOCK:
        if _CORE is not None:
            return _CORE
        path = _lk_path()
        name = 'look_native_lo_core'
        loader = importlib.machinery.SourceFileLoader(name, str(path))
        spec = importlib.util.spec_from_loader(name, loader)
        if spec is None:
            raise RuntimeError(f'cannot load LOOK core: {path}')
        module = importlib.util.module_from_spec(spec)
        sys.modules[name] = module
        loader.exec_module(module)
        _CORE = module
        return module


def _load_web_key() -> None:
    """Import only the known Ollama key from LOOK's user secret file.

    Signal is a service and does not inherit interactive zsh startup state.  Do
    not source arbitrary shell code just to recover one credential.
    """
    if os.environ.get('OLLAMA_API_KEY'):
        return
    path = Path.home()/'.zsh_secrets'
    try:
        text = path.read_text(encoding='utf-8', errors='replace')
    except OSError:
        return
    match = re.search(r'^\s*(?:export\s+)?OLLAMA_API_KEY\s*=\s*(.+?)\s*$', text, re.M)
    if not match:
        return
    raw = match.group(1).strip()
    try:
        parts = shlex.split(raw, posix=True)
        value = parts[0] if len(parts) == 1 else ''
    except ValueError:
        value = raw.strip('"\'')
    if value:
        os.environ['OLLAMA_API_KEY'] = value


class EventCollector:
    def __init__(self):
        self.rows=[]
        self.seq=0

    def emit(self,event,**fields):
        self.seq += 1
        row={'event':str(event),'seq':self.seq}
        row.update({k:v for k,v in fields.items() if v is not None})
        self.rows.append(row)


def available() -> bool:
    try:
        _load_core()
        return True
    except Exception:
        return False


def chat_once(prompt: str, *, profile='workspace', workspace=None, selected_paths=None,
              history=None, interface_context=None):
    """Run one LO operator turn and return structured machine data."""
    core=_load_core()
    _load_web_key()
    events=EventCollector()
    out=io.StringIO()
    err=io.StringIO()
    workspace=str(Path(workspace or Path.cwd()).expanduser().resolve())
    selected_paths=[str(Path(p).expanduser().resolve()) for p in (selected_paths or [])]

    # LOOK's UI renderer still writes human diagnostics internally.  Native
    # callers consume EventCollector instead; stdout/stderr never become a protocol.
    with _CHAT_LOCK, contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        old=os.environ.get('LOOK_PRESENTATION')
        os.environ['LOOK_PRESENTATION']='browser'
        try:
            rc=core.ollama_chat(
                initial_prompt=str(prompt), allow_start=True,
                access_profile=profile, selected_paths=selected_paths,
                workspace_override=workspace, one_shot=True, events=events,
                conversation_history=history or [], interface_context=interface_context,
            )
        finally:
            if old is None:
                os.environ.pop('LOOK_PRESENTATION',None)
            else:
                os.environ['LOOK_PRESENTATION']=old

    response=''
    error=''
    for row in events.rows:
        if row.get('event')=='response' and str(row.get('text') or '').strip():
            response=str(row['text']).strip()
        elif row.get('event')=='error':
            error=str(row.get('error') or row.get('message') or 'LO request failed')
    if int(rc or 0) != 0 and not error:
        error=(err.getvalue() or out.getvalue() or f'LO exited {rc}').strip().splitlines()[-1]
    if error:
        raise RuntimeError(error)
    if not response:
        raise RuntimeError('LO completed without a final response')
    return {'text':response,'events':events.rows,'returncode':int(rc or 0)}
