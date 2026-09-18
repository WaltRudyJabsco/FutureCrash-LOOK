#!/usr/bin/env python3
"""Tiny application-side client for Fabric Work Packets.

Apps request capabilities; this module handles node choice, packet submission and
result waiting. It deliberately contains no application semantics.
"""
from __future__ import annotations
import json, time, urllib.request, urllib.error, uuid

DEFAULT_NODE = "http://127.0.0.1:7332"

def _json(url, payload=None, timeout=5.0):
    data = None if payload is None else json.dumps(payload).encode()
    req = urllib.request.Request(url, data=data, headers={"Content-Type":"application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8","replace"))

def _nodes(base):
    return _json(base.rstrip('/')+"/v1/nodes", timeout=2.0)

def _candidates(snapshot):
    rows=[]
    me=snapshot.get("self") or {}
    rows.append((me.get("name") or "local", None, me))
    for p in snapshot.get("peers") or []:
        ad=p.get("node")
        if not ad: continue
        name=((ad.get("identity") or {}).get("name") or p.get("name"))
        rows.append((name,p.get("dns"),ad))
    return rows

def choose_node(base=DEFAULT_NODE, *, model=None, requires=None, latency=False):
    """Choose the soonest plausible capable worker using only advertised facts."""
    snap=_nodes(base); scored=[]
    requires=set(requires or ["text"])
    for name,dns,ad in _candidates(snap):
        caps=ad.get("capabilities") or {}
        inf=ad.get("inference") or {}
        models=inf.get("models") or []
        if "text" in requires and not inf.get("available", bool(models)): continue
        eligible=[]
        for m in models:
            f=m.get("features") or {}
            if model and m.get("name") != model: continue
            if any(r in {"vision","tools","thinking","embedding"} and not f.get(r) for r in requires): continue
            eligible.append(m)
        if not eligible: continue
        active=(ad.get("supervisor") or {}).get("active")
        resident=any(m.get("resident") for m in eligible)
        smallest=min(int(m.get("size") or 10**18) for m in eligible)
        # Availability dominates. Warmth dominates transfer/load cost. For reflex work,
        # smaller models break ties; otherwise locality is a mild preference.
        score=(0 if not active else 1000) + (0 if resident else 100) + (smallest/1e9 if latency else 0) + (0 if dns is None else 1)
        scored.append((score,name,dns,eligible))
    if not scored: raise RuntimeError("Fabric has no worker satisfying this inference request")
    scored.sort(key=lambda x:x[0])
    return scored[0]

def infer(messages, *, model=None, requires=None, latency=False, priority="interactive",
          think=False, options=None, timeout=90, base=DEFAULT_NODE, owner="app"):
    score,target,dns,eligible=choose_node(base,model=model,requires=requires,latency=latency)
    chosen=model
    if not chosen:
        pool=sorted(eligible,key=lambda m:int(m.get("size") or 0))
        chosen=(pool[0] if latency else pool[-1]).get("name")
    packet={
      "fabric":"fwp/1","kind":"task","origin":owner,
      "relationships":{},
      "work":{"operation":"model.infer","objective":"model inference",
              "input":{"model":chosen,"messages":messages,"think":think,
                       "options":options or {},"timeout":timeout}},
      "capabilities":{"requires":requires or ["text"],"prefers":{"latency":"low" if latency else "normal"}},
      "context":{},
      "execution":{"priority":priority,"cancellable":True,"budget":{"wall_ms":int(timeout*1000)+5000,"child_jobs":0,"depth":0}},
      "authority":{"principal":"user","grants":["model.infer"],"confirmed_operations":[]},
      "delivery":{"target":target},"provenance":{},"extensions":{"futurecrash":{"owner":owner}},
    }
    submit=_json(base.rstrip('/')+"/v1/jobs",{"packet":packet},timeout=6.0)
    job=(submit.get("job") or {}); jid=job.get("id") or packet.get("id")
    pollbase=(f"https://{dns}:7332" if dns else base.rstrip('/'))
    deadline=time.monotonic()+timeout+8
    while time.monotonic()<deadline:
        state=_json(pollbase+f"/v1/jobs/{jid}",timeout=4.0)
        status=state.get("status")
        if status in {"ok","failed","denied","cancelled"}:
            if status!="ok": raise RuntimeError(state.get("error") or f"Fabric inference {status}")
            result=state.get("result") or {}
            out=((result.get("work") or {}).get("output") or {})
            out["fabric_node"]=target
            return out
        time.sleep(.08)
    raise TimeoutError(f"Fabric inference timed out on {target}")
