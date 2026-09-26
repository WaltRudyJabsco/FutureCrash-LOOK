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


def route_intent(prompt: str) -> str:
    """Expose LOOK's shared front-door router to browser/native surfaces."""
    core=_load_core()
    fn=getattr(core,"_lo_intent_family",None)
    return str(fn(prompt) if callable(fn) else "general")


def analyze_request(prompt: str) -> dict:
    """Expose the same bounded cognition route used by terminal LO."""
    core=_load_core()
    fn=getattr(core,"_lo_cognition_route",None)
    if not callable(fn):
        return {"primary":route_intent(prompt),"families":[route_intent(prompt)],"confidence":0.5,"margin":0.0,"source":"compat","allowed_tools":[],"needs_clarification":False}
    route=fn(prompt)
    return route.public() if hasattr(route,"public") else dict(route)


def action_registry() -> list[dict]:
    """Machine-readable shared action vocabulary for every presentation surface."""
    core=_load_core()
    mod=getattr(core,"_cognition_module",lambda:None)()
    return list(mod.public_registry()) if mod and hasattr(mod,"public_registry") else []


def resolve_name(query: str, candidates: list[dict]) -> dict:
    """Fuzzy referent resolution without granting execution authority."""
    core=_load_core(); mod=getattr(core,"_cognition_module",lambda:None)()
    if not mod: return {"status":"no_match","confidence":0.0}
    return mod.resolve_name(query,candidates)


def available() -> bool:
    try:
        _load_core()
        return True
    except Exception:
        return False


def chat_once(prompt: str, *, profile='workspace', workspace=None, selected_paths=None,
              history=None, interface_context=None, persona=None, force_search=False):
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
        old_persona=os.environ.get('LOOK_LO_PERSONALITY')
        os.environ['LOOK_PRESENTATION']='browser'
        if persona:
            os.environ['LOOK_LO_PERSONALITY']=str(persona).strip().lower()
        try:
            rc=core.ollama_chat(
                force_search=bool(force_search), initial_prompt=str(prompt), allow_start=True,
                access_profile=profile, selected_paths=selected_paths,
                workspace_override=workspace, one_shot=True, events=events,
                conversation_history=history or [], interface_context=interface_context,
            )
        finally:
            if old is None:
                os.environ.pop('LOOK_PRESENTATION',None)
            else:
                os.environ['LOOK_PRESENTATION']=old
            if persona:
                if old_persona is None:
                    os.environ.pop('LOOK_LO_PERSONALITY',None)
                else:
                    os.environ['LOOK_LO_PERSONALITY']=old_persona

    response=''
    error=''
    receipts=[]
    route=None
    goal=None
    satisfaction=None
    plan=None
    for row in events.rows:
        if row.get('event')=='response' and str(row.get('text') or '').strip():
            response=str(row['text']).strip()
        elif row.get('event')=='source_receipt':
            receipts.append({k:row.get(k) for k in ('edge','source','confidence','as_of','retrieved_at','source_url') if row.get(k) is not None})
        elif row.get('event')=='intent_routed':
            route={k:row.get(k) for k in ('family','families','confidence','margin','source','forced_search') if row.get(k) is not None}
        elif row.get('event')=='goal_started':
            goal={k:v for k,v in row.items() if k not in {'event','seq'}}
        elif row.get('event')=='plan_created':
            plan={k:v for k,v in row.items() if k not in {'event','seq'}}
        elif row.get('event')=='goal_verified':
            satisfaction={k:v for k,v in row.items() if k not in {'event','seq'}}
        elif row.get('event')=='error':
            error=str(row.get('error') or row.get('message') or 'LO request failed')
    if int(rc or 0) != 0 and not error:
        error=(err.getvalue() or out.getvalue() or f'LO exited {rc}').strip().splitlines()[-1]
    if error:
        raise RuntimeError(error)
    if not response:
        raise RuntimeError('LO completed without a final response')
    # Provenance is evidence, not a confidence score. If no deterministic/search
    # receipt backed the turn, callers can truthfully label the prose MODEL rather
    # than accidentally presenting model synthesis as sourced fact.
    provenance = receipts[-1] if receipts else {'edge':'MODEL','source':'model','confidence':'INFERRED'}
    return {'text':response,'events':events.rows,'returncode':int(rc or 0),
            'persona':str(persona or ''),'receipts':receipts,'provenance':provenance,
            'route':route,'goal':goal,'plan':plan,'satisfaction':satisfaction}
