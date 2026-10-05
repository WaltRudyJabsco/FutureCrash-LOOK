#!/usr/bin/env python3
"""Capability Curator: deterministic discovery and empirical qualification.

The curator answers one narrow question: what typed operations can this node
actually perform, and through which host adapter? Discovery is non-destructive;
ordinary successful use upgrades discovered adapters to proven ones.
"""
from __future__ import annotations

import json, os, platform, shutil, time
from pathlib import Path
from typing import Any

SCHEMA_VERSION=1
DEFAULT_PATH=Path.home()/".local/share/future-crash-look/capabilities.json"

WINDOW_ACTIONS=("close","focus","maximize","minimize","fullscreen")

def _which(name:str)->str:
    return shutil.which(name) or ""

def discover() -> dict[str,Any]:
    system=platform.system().casefold()
    adapters=[]
    if system=="darwin":
        osa=_which("osascript")
        if osa:
            adapters.append({
                "id":"macos-terminal-applescript","kind":"terminal_window","path":osa,
                "actions":["close","focus","maximize","fullscreen"],
                "confidence":0.90,"state":"discovered",
                "notes":"Terminal window id + AppleScript/System Events",
            })
    elif system=="linux":
        adapters.append({
            "id":"linux-terminal-control","kind":"terminal_window","path":"typed-fifo",
            "actions":["focus","maximize","minimize","fullscreen"],
            "confidence":0.72,"state":"discovered",
            "notes":"zero-dependency terminal control channel; dispatch is observable, visual effect is not",
        })
        wmctrl=_which("wmctrl")
        if wmctrl:
            adapters.append({
                "id":"linux-wmctrl","kind":"terminal_window","path":wmctrl,
                "actions":["close","focus","maximize","fullscreen"],
                "confidence":0.92,"state":"discovered",
                "notes":"EWMH window control; requires a visible matching window",
            })
        xdotool=_which("xdotool")
        if xdotool:
            adapters.append({
                "id":"linux-xdotool","kind":"terminal_window","path":xdotool,
                "actions":["close","focus","minimize"],
                "confidence":0.82,"state":"discovered",
                "notes":"X11/XWayland fallback",
            })
        # Process-handle close is available even on Wayland and needs no package.
        adapters.append({
            "id":"linux-process-handle","kind":"terminal_window","path":"os.kill",
            "actions":["close"],"confidence":0.98,"state":"discovered",
            "notes":"typed child-process handle; display-server independent",
        })
    return {
        "schema":SCHEMA_VERSION,"generated_at":time.time(),"platform":system,
        "node":platform.node(),"adapters":adapters,
    }

def _load(path:Path=DEFAULT_PATH)->dict[str,Any]:
    try:
        data=json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data,dict) else {}
    except (OSError,json.JSONDecodeError):
        return {}

def refresh(path:Path=DEFAULT_PATH)->dict[str,Any]:
    previous=_load(path)
    learned={str(a.get("id")):a for a in previous.get("adapters",[]) if isinstance(a,dict)}
    data=discover()
    for row in data["adapters"]:
        old=learned.get(row["id"],{})
        if old.get("state")=="proven":
            row["state"]="proven"
            row["confidence"]=max(float(row.get("confidence",0)),float(old.get("confidence",0)))
            row["successes"]=int(old.get("successes",0))
            row["failures"]=int(old.get("failures",0))
            row["last_success_at"]=float(old.get("last_success_at",0) or 0)
        elif old:
            row["successes"]=int(old.get("successes",0)); row["failures"]=int(old.get("failures",0))
    path.parent.mkdir(parents=True,exist_ok=True)
    tmp=path.with_suffix(path.suffix+".tmp")
    tmp.write_text(json.dumps(data,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    try: os.chmod(tmp,0o600)
    except OSError: pass
    tmp.replace(path)
    return data

def catalog(path:Path=DEFAULT_PATH,*,auto_refresh:bool=True)->dict[str,Any]:
    data=_load(path)
    stale=time.time()-float(data.get("generated_at",0) or 0)>24*60*60
    return refresh(path) if auto_refresh and (not data or stale) else data

def adapters_for(kind:str,action:str,path:Path=DEFAULT_PATH)->list[dict[str,Any]]:
    rows=[]
    for row in catalog(path).get("adapters",[]):
        if row.get("kind")==kind and action in (row.get("actions") or []): rows.append(dict(row))
    return sorted(rows,key=lambda r:(r.get("state")!="proven",-float(r.get("confidence",0))))

def supports(kind:str,action:str,path:Path=DEFAULT_PATH)->bool:
    return bool(adapters_for(kind,action,path))

def record_result(adapter_id:str,action:str,ok:bool,path:Path=DEFAULT_PATH)->None:
    data=catalog(path)
    changed=False
    for row in data.get("adapters",[]):
        if row.get("id")!=adapter_id: continue
        key="successes" if ok else "failures"; row[key]=int(row.get(key,0))+1
        row["last_action"]=action; row["last_observed_at"]=time.time()
        if ok:
            row["state"]="proven"; row["last_success_at"]=time.time(); row["confidence"]=max(.99,float(row.get("confidence",0)))
        changed=True; break
    if changed:
        tmp=path.with_suffix(path.suffix+".tmp"); tmp.write_text(json.dumps(data,indent=2,sort_keys=True)+"\n",encoding="utf-8"); tmp.replace(path)

def public_capabilities(path:Path=DEFAULT_PATH)->dict[str,bool]:
    data=catalog(path)
    platform_name=str(data.get("platform") or "")
    out={
        "capability.catalog":True,"state.live":True,"state.observe":True,
        "state.observe.windows": bool((platform_name=="linux" and _which("wmctrl")) or (platform_name=="darwin" and _which("osascript"))),
    }
    for action in WINDOW_ACTIONS:
        out[f"window.{action}"]=any(r.get("kind")=="terminal_window" and action in (r.get("actions") or []) for r in data.get("adapters",[]))
    return out
