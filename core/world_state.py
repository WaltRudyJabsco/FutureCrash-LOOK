#!/usr/bin/env python3
"""Persistent typed world state for LOOK/LO.

Language is not the system of record. This module stores compact goals, task
steps, action receipts, failures, and wake events so cognition can resume from
machine truth instead of reconstructing it from chat prose.
"""
from __future__ import annotations

import json
import os
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

SCHEMA_VERSION=1
MAX_RECEIPTS=96
MAX_EVENTS=96
MAX_GOALS=32

@dataclass(frozen=True)
class TypedReceipt:
    id: str
    action: str
    ok: bool
    status: str
    message: str
    observed_at: float
    goal_id: str = ""
    args: dict[str,Any] = field(default_factory=dict)
    duration_ms: int = 0
    failure_class: str = ""

    def public(self) -> dict[str,Any]:
        return asdict(self)


def _empty() -> dict[str,Any]:
    return {
        "schema_version":SCHEMA_VERSION,
        "updated_at":0.0,
        "active_goal_id":"",
        "goals":[],
        "receipts":[],
        "events":[],
    }


def classify_failure(status: str, message: str) -> str:
    status=str(status or "").casefold(); text=str(message or "")
    low=text.casefold()
    if status=="internal_error" or "traceback" in low or "nameerror" in low:
        return "host_bug"
    if "permission denied" in low or "not permitted" in low or "denied" in low:
        return "permission"
    if "no such file or directory" in low or "not found" in low:
        return "missing_resource"
    if "timed out" in low or "timeout" in low:
        return "transient_or_timeout"
    if "blocked" in low or "guard" in low:
        return "policy_guard"
    return "action_failure"


def execution_policy(action: str) -> dict[str,Any]:
    """Return structural execution policy; models do not choose consequence level."""
    action=str(action or "")
    destructive={"remove_path"}
    mutations={"write_file","create_text_files","copy_path","move_path","make_directory"}
    consequential={"run_command","close_object","schedule_prompt","generate_image","media_play","media_queue","media_control","audio_speak","open_path","open_url"}
    if action in destructive:
        return {"mode":"deliberate","preflight":True,"verify":True,"risk":"destructive"}
    if action in mutations:
        return {"mode":"deliberate","preflight":True,"verify":True,"risk":"mutation"}
    if action in consequential:
        return {"mode":"deliberate","preflight":True,"verify":True,"risk":"effect"}
    return {"mode":"normal","preflight":False,"verify":False,"risk":"read"}


class WorldState:
    def __init__(self,path: str|Path):
        self.path=Path(path)

    def load(self) -> dict[str,Any]:
        try:
            data=json.loads(self.path.read_text(encoding="utf-8"))
            if not isinstance(data,dict): return _empty()
        except (OSError,json.JSONDecodeError):
            return _empty()
        out=_empty(); out.update(data)
        for key in ("goals","receipts","events"):
            if not isinstance(out.get(key),list): out[key]=[]
        return out

    def save(self,state: dict[str,Any]) -> None:
        self.path.parent.mkdir(parents=True,exist_ok=True)
        row=dict(state); row["schema_version"]=SCHEMA_VERSION; row["updated_at"]=time.time()
        row["goals"]=list(row.get("goals") or [])[-MAX_GOALS:]
        row["receipts"]=list(row.get("receipts") or [])[-MAX_RECEIPTS:]
        row["events"]=list(row.get("events") or [])[-MAX_EVENTS:]
        tmp=self.path.with_suffix(self.path.suffix+".tmp")
        tmp.write_text(json.dumps(row,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
        try: os.chmod(tmp,0o600)
        except OSError: pass
        tmp.replace(self.path)
        try: os.chmod(self.path,0o600)
        except OSError: pass

    def begin_goal(self,goal: Any,*,wake_on: str="operator_or_receipt") -> dict[str,Any]:
        public=goal.public() if hasattr(goal,"public") else dict(goal or {})
        gid=str(public.get("id") or "")
        if not gid: return {}
        state=self.load(); goals=[g for g in state["goals"] if g.get("id")!=gid]
        row={
            "id":gid,"request":str(public.get("request") or "")[:1000],
            "primary":str(public.get("primary") or "general"),
            "families":list(public.get("families") or []),"status":"running",
            "created":float(public.get("created") or time.time()),"updated_at":time.time(),
            "wake_on":wake_on,"close_when":"satisfied_failed_or_cancelled",
            "steps":list(public.get("steps") or []),
        }
        goals.append(row); state["goals"]=goals; state["active_goal_id"]=gid
        state["events"].append({"kind":"goal_started","goal_id":gid,"at":time.time()})
        self.save(state); return row

    def begin_action(self,action: str,*,args: dict[str,Any]|None=None) -> dict[str,Any]:
        state=self.load(); gid=str(state.get("active_goal_id") or "")
        policy=execution_policy(action)
        state["events"].append({
            "kind":"action_preflight","goal_id":gid,"action":str(action),
            "policy":policy,"args":dict(args or {}),"at":time.time(),
        })
        self.save(state)
        return policy

    def record_receipt(self,action: str,ok: bool,status: str,message: str,*,args: dict[str,Any]|None=None,duration_ms: int=0) -> dict[str,Any]:
        state=self.load(); gid=str(state.get("active_goal_id") or "")
        rid=f"rcpt_{int(time.time()*1000):x}_{len(state['receipts'])%256:02x}"
        failure="" if ok else classify_failure(status,message)
        receipt=TypedReceipt(rid,str(action),bool(ok),str(status),str(message)[:2000],time.time(),gid,dict(args or {}),int(duration_ms or 0),failure).public()
        state["receipts"].append(receipt)
        state["events"].append({"kind":"receipt","receipt_id":rid,"goal_id":gid,"action":str(action),"ok":bool(ok),"at":time.time()})
        if gid:
            for goal in state["goals"]:
                if goal.get("id")!=gid: continue
                goal["updated_at"]=time.time()
                for step in goal.get("steps") or []:
                    actions=[str(x).split(".")[-1] for x in (step.get("actions") or [])]
                    canonical=str(action).replace("_","")
                    if any(str(x).replace("_","").replace(".","").endswith(canonical) for x in step.get("actions") or []):
                        step["status"]="done" if ok else "failed"
                        step["receipt_id"]=rid
                        break
                if not ok:
                    goal["status"]="waiting_event" if failure=="transient_or_timeout" else "failed"
                    goal["last_failure_receipt"]=rid
                    goal["wake_on"]="operator_retry_or_environment_change"
                break
        self.save(state); return receipt

    def close_goal(self,goal_id: str,*,satisfied: bool,reason: str="") -> None:
        if not goal_id: return
        state=self.load()
        for goal in state["goals"]:
            if goal.get("id")==goal_id:
                goal["status"]="done" if satisfied else "failed"
                goal["outcome"]=str(reason)[:1000]
                goal["updated_at"]=time.time()
                break
        if state.get("active_goal_id")==goal_id: state["active_goal_id"]=""
        state["events"].append({"kind":"goal_closed","goal_id":goal_id,"satisfied":bool(satisfied),"at":time.time()})
        self.save(state)

    def wake(self,reason: str,*,goal_id: str="") -> None:
        state=self.load(); gid=goal_id or str(state.get("active_goal_id") or "")
        state["events"].append({"kind":"wake","goal_id":gid,"reason":str(reason)[:500],"at":time.time()})
        if gid:
            for goal in state["goals"]:
                if goal.get("id")==gid and goal.get("status") not in {"done","cancelled"}:
                    goal["status"]="ready"; goal["updated_at"]=time.time(); break
        self.save(state)

    def latest_failure(self) -> dict[str,Any]|None:
        for row in reversed(self.load()["receipts"]):
            if not row.get("ok"): return row
        return None

    def latest_receipts(self,limit: int=6) -> list[dict[str,Any]]:
        return self.load()["receipts"][-max(1,int(limit)):]

    def context(self,limit: int=5) -> str:
        state=self.load(); lines=["TYPED WORLD STATE (host authoritative; never reconstruct these facts from prose):"]
        gid=str(state.get("active_goal_id") or "")
        if gid:
            goal=next((g for g in reversed(state["goals"]) if g.get("id")==gid),None)
            if goal: lines.append(f"ACTIVE GOAL: {gid} · {goal.get('status')} · {goal.get('request','')}")
        rows=state["receipts"][-max(1,int(limit)):]
        for row in rows:
            mark="OK" if row.get("ok") else "FAILED"
            line=f"RECEIPT {row.get('id')}: {row.get('action')} {mark} [{row.get('status')}] {row.get('message','')}"
            if row.get("failure_class"): line+=f" · class={row.get('failure_class')}"
            lines.append(line[:2400])
        if len(lines)==1: return ""
        lines.append("RULE: a later explicit operator request is a new attempt; an earlier failure is evidence, never a veto on retry.")
        return "\n".join(lines)
