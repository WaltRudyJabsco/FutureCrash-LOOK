#!/usr/bin/env python3
"""Bounded present-tense state for LOOK/LO.

WorldState is durable forensic history. LiveState is different: it keeps a small
refreshable set of facts that are useful *now* (objects, focus-ish recency,
services, referents). Facts carry provenance, freshness and TTL; stale objects
are refreshed or retired rather than becoming permanent memory.
"""
from __future__ import annotations

import json, os, time
from pathlib import Path
from typing import Any

SCHEMA_VERSION=1
DEFAULT_PATH=Path.home()/".local/share/future-crash-look/live_state.json"
MAX_OBJECTS=96
MAX_FACTS=128

TTL_BY_KIND={
    "terminal_window":8.0,
    "process":5.0,
    "service":20.0,
    "browser_window":5.0,
    "browser_tab":5.0,
}


def _now()->float: return time.time()

def _empty()->dict[str,Any]:
    return {"schema":SCHEMA_VERSION,"updated_at":0.0,"objects":[],"facts":[],"current_object_id":""}

def _load(path:Path)->dict[str,Any]:
    try:
        data=json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data,dict): return _empty()
    except (OSError,json.JSONDecodeError):
        return _empty()
    out=_empty(); out.update(data)
    if not isinstance(out.get("objects"),list): out["objects"]=[]
    if not isinstance(out.get("facts"),list): out["facts"]=[]
    return out

def _save(path:Path,data:dict[str,Any])->None:
    data=dict(data); data["schema"]=SCHEMA_VERSION; data["updated_at"]=_now()
    data["objects"]=list(data.get("objects") or [])[-MAX_OBJECTS:]
    data["facts"]=list(data.get("facts") or [])[-MAX_FACTS:]
    path.parent.mkdir(parents=True,exist_ok=True)
    tmp=path.with_suffix(path.suffix+".tmp")
    tmp.write_text(json.dumps(data,ensure_ascii=False,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    try: os.chmod(tmp,0o600)
    except OSError: pass
    tmp.replace(path)
    try: os.chmod(path,0o600)
    except OSError: pass


def _object_id(ref:dict[str,Any])->str:
    return str(ref.get("id") or ref.get("os_window_id") or ref.get("pid") or ref.get("window_token") or "").strip()

def _pid_from_ref(ref:dict[str,Any])->int:
    try:
        pid=int(ref.get("pid") or 0)
        if pid>1: return pid
    except (TypeError,ValueError): pass
    raw=str(ref.get("pid_file") or "").strip()
    if raw:
        try:
            pid=int(Path(raw).read_text(encoding="utf-8").strip())
            if pid>1: return pid
        except (OSError,ValueError): pass
    try:
        pid=int(ref.get("launcher_pid") or 0)
        return pid if pid>1 else 0
    except (TypeError,ValueError):
        return 0

def _pid_alive(pid:int)->bool:
    if pid<=1: return False
    try: os.kill(pid,0); return True
    except PermissionError: return True
    except OSError: return False


def _fresh(row:dict[str,Any],now:float|None=None)->bool:
    if row.get("status") in {"closed","retired"}: return False
    now=_now() if now is None else now
    try:
        ttl=float(row.get("ttl",TTL_BY_KIND.get(str(row.get("kind") or "object"),15.0)) or 0)
        observed=float(row.get("observed_at",0) or 0)
    except (TypeError,ValueError): return False
    return bool(observed and (ttl<=0 or now-observed<=ttl))


def observe_object(ref:dict[str,Any],*,path:Path=DEFAULT_PATH,source:str="host_receipt",ttl:float|None=None,current:bool=True)->dict[str,Any]:
    """Upsert one typed live object from authoritative host evidence."""
    ref=dict(ref or {}); oid=_object_id(ref)
    if not oid: return {}
    now=_now(); kind=str(ref.get("kind") or "object")
    data=_load(path); rows=[]; old={}
    for row in data["objects"]:
        if str(row.get("id") or "") == oid: old=dict(row)
        else: rows.append(row)
    merged=dict(old); merged.update(ref)
    merged.update({
        "id":oid,"kind":kind,"status":str(ref.get("status") or old.get("status") or "open"),
        "observed_at":now,"source":source,"ttl":float(ttl if ttl is not None else TTL_BY_KIND.get(kind,15.0)),
        "confidence":1.0 if source in {"host_receipt","inspector"} else float(old.get("confidence",.8)),
    })
    if not merged.get("created_at"):
        merged["created_at"]=now
    pid=_pid_from_ref(merged)
    if pid: merged["pid"]=pid
    rows.append(merged); data["objects"]=rows
    if current: data["current_object_id"]=oid
    _save(path,data); return merged


def retire_object(ref_or_id:dict[str,Any]|str,*,path:Path=DEFAULT_PATH,reason:str="closed",source:str="host_receipt")->None:
    oid=_object_id(ref_or_id) if isinstance(ref_or_id,dict) else str(ref_or_id or "")
    if not oid: return
    data=_load(path); now=_now()
    for row in data["objects"]:
        if str(row.get("id") or "")!=oid: continue
        row["status"]="closed"; row["retired_at"]=now; row["retire_reason"]=reason; row["source"]=source; row["observed_at"]=now
    if data.get("current_object_id")==oid: data["current_object_id"]=""
    _save(path,data)


def record_fact(key:str,value:Any,*,path:Path=DEFAULT_PATH,source:str="host",ttl:float=30.0)->None:
    data=_load(path); now=_now(); rows=[r for r in data["facts"] if str(r.get("key"))!=str(key)]
    rows.append({"key":str(key),"value":value,"observed_at":now,"ttl":float(ttl),"source":source,"confidence":1.0})
    data["facts"]=rows; _save(path,data)


def refresh(*,path:Path=DEFAULT_PATH)->dict[str,Any]:
    """Refresh cheap facts and retire objects we can prove are gone.

    Unknown display state is left stale rather than guessed. Linux terminal
    objects are cheaply reconciled through their process handle. Other object
    classes can add authoritative inspectors without changing the state contract.
    """
    data=_load(path); now=_now(); changed=False
    for row in data["objects"]:
        if row.get("status") in {"closed","retired"}: continue
        kind=str(row.get("kind") or "")
        if kind=="terminal_window" and str(row.get("platform") or "").startswith("linux"):
            pid=_pid_from_ref(row)
            if pid and not _pid_alive(pid):
                row["status"]="closed"; row["retired_at"]=now; row["retire_reason"]="process_gone"; row["source"]="process_inspector"; row["observed_at"]=now; changed=True
            elif pid:
                row["pid"]=pid; row["observed_at"]=now; row["source"]="process_inspector"; changed=True
    if changed: _save(path,data)
    return data



def reconcile_domain(domain:str,observed:list[dict[str,Any]],*,path:Path=DEFAULT_PATH,source:str="inspector",authoritative:bool=False)->dict[str,Any]:
    """Merge one observed world domain into Live State.

    Authoritative reconciliation may retire objects previously seen by the same
    observation domain when they disappear. Receipt-only objects are preserved
    unless an observed object can be matched to them or another inspector proves
    they are gone.
    """
    data=_load(path); now=_now(); domain=str(domain or "").strip()
    rows=[dict(r) for r in data.get("objects",[])]
    by_id={str(r.get("id") or ""):r for r in rows if str(r.get("id") or "")}
    seen=set()
    for raw in list(observed or []):
        if not isinstance(raw,dict): continue
        obj=dict(raw); oid=_object_id(obj)
        if not oid: continue
        # Prefer stable LOOK identity. If a desktop observer only gives us a raw
        # OS window id, reconcile by process id against an existing typed object.
        try: opid=int(obj.get("pid") or 0)
        except (TypeError,ValueError): opid=0
        if oid not in by_id:
            owid=str(obj.get("os_window_id") or "").strip()
            if owid:
                matches=[rid for rid,row in by_id.items() if str(row.get("os_window_id") or "").strip()==owid and row.get("status") not in {"closed","retired"}]
                if len(matches)==1: oid=matches[0]; obj["id"]=oid
        if oid not in by_id and opid>1:
            matches=[rid for rid,row in by_id.items() if _pid_from_ref(row)==opid and row.get("status") not in {"closed","retired"}]
            if len(matches)==1: oid=matches[0]; obj["id"]=oid
        old=by_id.get(oid,{})
        merged=dict(old); merged.update(obj)
        merged.update({"id":oid,"status":"open","observed_at":now,"source":source,"domain":domain,"confidence":1.0})
        if "ttl" not in merged: merged["ttl"]=float(TTL_BY_KIND.get(str(merged.get("kind") or "object"),15.0))
        by_id[oid]=merged; seen.add(oid)
        if bool(merged.get("focused")):
            data["current_object_id"]=oid
    if authoritative:
        for oid,row in list(by_id.items()):
            if row.get("status") in {"closed","retired"}: continue
            if str(row.get("domain") or "")==domain and str(row.get("source") or "").endswith("inspector") and oid not in seen:
                row["status"]="closed"; row["retired_at"]=now; row["retire_reason"]="not_observed"; row["observed_at"]=now; row["source"]=source
    data["objects"]=list(by_id.values())
    if data.get("current_object_id") and data["current_object_id"] not in {r.get("id") for r in data["objects"] if r.get("status") not in {"closed","retired"}}:
        data["current_object_id"]=""
    record={"key":f"observation.{domain}","value":{"count":len(seen),"authoritative":bool(authoritative)},"observed_at":now,"ttl":5.0,"source":source,"confidence":1.0}
    data["facts"]=[r for r in data.get("facts",[]) if str(r.get("key"))!=record["key"]]+[record]
    _save(path,data); return snapshot(path=path)

def active_objects(*,path:Path=DEFAULT_PATH,kind:str="",refresh_now:bool=True)->list[dict[str,Any]]:
    data=refresh(path=path) if refresh_now else _load(path)
    now=_now()
    rows=[dict(r) for r in data["objects"] if _fresh(r,now) and (not kind or r.get("kind")==kind)]
    current=str(data.get("current_object_id") or "")
    rows.sort(key=lambda r:(str(r.get("id"))!=current,-float(r.get("observed_at",0) or 0)))
    return rows


def current_object(*,path:Path=DEFAULT_PATH)->dict[str,Any]|None:
    data=refresh(path=path); oid=str(data.get("current_object_id") or "")
    if not oid: return None
    for row in data["objects"]:
        if str(row.get("id"))==oid and _fresh(row): return dict(row)
    return None


def snapshot(*,path:Path=DEFAULT_PATH)->dict[str,Any]:
    data=refresh(path=path); now=_now()
    objects=[]
    for row in data["objects"]:
        if not _fresh(row,now): continue
        item=dict(row); item["age_ms"]=max(0,int((now-float(row.get("observed_at",now)))*1000)); objects.append(item)
    facts=[]
    for row in data["facts"]:
        age=now-float(row.get("observed_at",0) or 0)
        if age <= float(row.get("ttl",0) or 0):
            item=dict(row); item["age_ms"]=max(0,int(age*1000)); facts.append(item)
    return {"schema":SCHEMA_VERSION,"observed_at":now,"current_object_id":data.get("current_object_id","") ,"objects":objects,"facts":facts}


def relevant_context(prompt:str,*,path:Path=DEFAULT_PATH,limit:int=12)->str:
    """Return a compact state slice selected by deterministic topic hints."""
    low=" ".join(str(prompt or "").casefold().split())
    wants_windows=any(w in low for w in ("window","terminal","maximize","fullscreen","full screen","minimize","focus","close it","close that","other one"))
    wants_process=any(w in low for w in ("process","running","pid","server","slow"))
    if not (wants_windows or wants_process): return ""
    snap=snapshot(path=path); rows=[]
    for obj in snap["objects"]:
        if wants_windows and obj.get("kind")!="terminal_window": continue
        rows.append(obj)
    rows=rows[:max(1,int(limit))]
    if not rows: return ""
    lines=["LIVE STATE (host-observed present tense; fresher than memory/chat):"]
    current=str(snap.get("current_object_id") or "")
    for row in rows:
        mark="CURRENT" if str(row.get("id"))==current else "LIVE"
        name=str(row.get("command") or row.get("title") or row.get("name") or "")
        src=str(row.get("source") or "host")
        age=int(row.get("age_ms") or 0)
        extra=[]
        if row.get("pid"): extra.append(f"pid={row['pid']}")
        if row.get("platform"): extra.append(str(row["platform"]))
        lines.append(f"{mark} {row.get('kind')} {row.get('id')} · {name} · {' · '.join(extra)} · [{src} {age}ms ago]")
    lines.append("RULE: use LIVE STATE for current object identity; use durable receipts as history, not as proof an object still exists.")
    return "\n".join(lines)
