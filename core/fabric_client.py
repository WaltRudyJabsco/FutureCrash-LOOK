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
    return _json(base.rstrip('/')+"/v1/nodes", timeout=4.0)

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

def choose_node(base=DEFAULT_NODE, *, model=None, requires=None, latency=False, exclude=None):
    """Choose the soonest plausible capable worker using only advertised facts."""
    snap=_nodes(base); scored=[]
    requires=set(requires or ["text"])
    excluded=set(exclude or [])
    for name,dns,ad in _candidates(snap):
        if name in excluded:
            continue
        runtime=ad.get("runtime") or {}
        if runtime and runtime.get("ok") is False:
            continue
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


def _ad_for_target(base, target):
    snap=_nodes(base)
    for name,dns,ad in _candidates(snap):
        if name==target:
            return ad
    return {}

def infer(messages, *, model=None, requires=None, latency=False, priority="interactive",
          think=False, options=None, timeout=90, base=DEFAULT_NODE, owner="app"):
    score,target,dns,eligible=choose_node(base,model=model,requires=requires,latency=latency)
    ad=_ad_for_target(base,target)
    chosen=model
    if not chosen:
        preferred=((ad.get("inference") or {}).get("preferred_model"))
        names={m.get("name") for m in eligible}
        if preferred in names:
            chosen=preferred
        else:
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
    # Submit work to the selected worker. delivery.target is descriptive/provenance;
    # transport placement must be real rather than relying on the origin node to
    # interpret a remote target later.
    pollbase=(f"https://{dns}:7332" if dns else base.rstrip('/'))
    submit=_json(pollbase+"/v1/jobs",{"packet":packet},timeout=6.0)
    job=(submit.get("job") or {}); jid=job.get("id") or packet.get("id")
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
        time.sleep(.25)
    raise TimeoutError(f"Fabric inference timed out on {target}")

def stream_infer(payload, *, requires=None, priority="interactive", timeout=180,
                 base=DEFAULT_NODE, owner="lo", route=None):
    """Route a mature Ollama chat payload to Fabric and yield its JSONL stream.

    A healthy turn remains sticky to one worker/model. Before the first streamed
    event, however, BUSY or transport failure is a placement failure, not a user
    failure: retry once on another eligible worker and update the turn route.
    """
    import socket

    model=payload.get("model") or None
    reqs=set(requires or ["text"])
    tried=set()
    max_attempts=3

    def select(prefer_route=True):
        if prefer_route and isinstance(route,dict) and route.get("target") and route.get("target") not in tried:
            target=str(route["target"]); dns=route.get("dns")
            ad=_ad_for_target(base,target)
            models=((ad.get("inference") or {}).get("models") or [])
            eligible=[]
            for m in models:
                features=m.get("features") or {}
                if model and m.get("name") != model: continue
                if any(r in {"vision","tools","thinking","embedding"} and not features.get(r) for r in reqs): continue
                eligible.append(m)
            if eligible:
                chosen=str(route.get("model") or model or "")
                if not chosen:
                    preferred=((ad.get("inference") or {}).get("preferred_model"))
                    names={m.get("name") for m in eligible}
                    chosen=preferred if preferred in names else max(eligible,key=lambda m:int(m.get("size") or 0)).get("name")
                return target,dns,chosen
        _,target,dns,eligible=choose_node(base,model=model,requires=reqs,latency=False,exclude=tried)
        ad=_ad_for_target(base,target)
        chosen=model
        if not chosen:
            preferred=((ad.get("inference") or {}).get("preferred_model"))
            names={m.get("name") for m in eligible}
            chosen=preferred if preferred in names else max(eligible,key=lambda m:int(m.get("size") or 0)).get("name")
        return target,dns,chosen

    last_error=None
    for attempt_no in range(max_attempts):
        try:
            target,dns,chosen=select(prefer_route=(attempt_no==0))
        except (urllib.error.URLError, TimeoutError, socket.timeout) as exc:
            # Route discovery is control-plane work.  A transient slow /v1/nodes
            # response should not leak a raw urllib timeout into LO.
            last_error=exc
            time.sleep(.15)
            continue
        if isinstance(route,dict):
            route.update({"target":target,"dns":dns,"model":chosen})
        inp={"model":chosen,"messages":payload.get("messages") or [],"timeout":timeout,
             "keep_alive":payload.get("keep_alive",-1),"options":payload.get("options") or {}}
        if "think" in payload: inp["think"]=payload.get("think")
        if isinstance(payload.get("tools"),list): inp["tools"]=payload["tools"]
        packet={
          "fabric":"fwp/1","kind":"task","origin":owner,"relationships":{},
          "work":{"operation":"model.infer","objective":"stream conversational inference","input":inp},
          "capabilities":{"requires":list(reqs),"prefers":{"latency":"normal"}},
          "context":{},"execution":{"priority":priority,"cancellable":True,
            "budget":{"wall_ms":int(timeout*1000)+5000,"child_jobs":0,"depth":0}},
          "authority":{"principal":"user","grants":["model.infer"],"confirmed_operations":[]},
          "delivery":{"target":target},"provenance":{},"extensions":{"futurecrash":{"owner":owner}},
        }
        endpoint=(f"https://{dns}:7332" if dns else base.rstrip('/'))+"/v1/infer/stream"
        req=urllib.request.Request(endpoint,data=json.dumps({"packet":packet}).encode(),
                                   headers={"Content-Type":"application/json"},method="POST")
        emitted=False
        try:
            with urllib.request.urlopen(req,timeout=timeout) as response:
                node=response.headers.get("X-Fabric-Node") or target
                for raw in response:
                    if raw.strip():
                        emitted=True
                        event=json.loads(raw)
                        event["_fabric_node"]=node
                        yield event
            return
        except urllib.error.HTTPError as exc:
            detail=exc.read().decode("utf-8","replace")
            try: detail=json.loads(detail).get("error") or detail
            except Exception: pass
            last_error=RuntimeError(f"Fabric inference HTTP {exc.code}: {detail}")
            # 409 before streaming means placement raced with another job. Re-route.
            if exc.code != 409 or emitted:
                raise last_error from None
        except (urllib.error.URLError, TimeoutError, socket.timeout) as exc:
            last_error=exc
            if emitted:
                raise
        tried.add(target)
        if isinstance(route,dict):
            route.clear()
        # Give a just-released lease a moment to settle, then try another worker.
        time.sleep(.15)
        try:
            choose_node(base,model=model,requires=reqs,latency=False,exclude=tried)
        except Exception:
            break
    if last_error:
        raise RuntimeError(f"Fabric inference unavailable after {len(tried)} worker attempt(s): {last_error}") from None
    raise RuntimeError("Fabric inference unavailable")
