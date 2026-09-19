#!/usr/bin/env python3
"""Tiny application-side client for Fabric Work Packets.

Apps request capabilities; this module handles node choice, packet submission and
result waiting. It deliberately contains no application semantics.
"""
from __future__ import annotations
import json, time, urllib.request, urllib.error, uuid

from conductor import classify as _classify_work, last_user_text as _last_user_text

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
    me_name=me.get("name") or ((me.get("identity") or {}).get("name")) or "local"
    rows.append((me_name, None, me))
    for p in snapshot.get("peers") or []:
        ad=p.get("node")
        if not ad: continue
        name=((ad.get("identity") or {}).get("name") or p.get("name"))
        rows.append((name,p.get("dns"),ad))
    return rows


def _find_target(snapshot, target):
    for name,dns,ad in _candidates(snapshot):
        if name == target:
            return dns,ad
    return None,{}


def _model_expected_ms(model, tier="balanced"):
    q=(model.get("qualification") or {})
    ttft=float(q.get("ttft_ms") or 900.0)
    tok=float(q.get("generation_tok_s") or 0.0)
    # Qualification evidence is intentionally modest.  It nudges placement but
    # never overrides hard capability requirements or availability.
    expected_tokens={"reflex":32.0,"balanced":120.0,"deep":320.0}.get(tier,120.0)
    generation=(expected_tokens/tok*1000.0) if tok>0 else 1200.0
    return ttft+generation

def _choose_from_snapshot(snapshot, *, model=None, requires=None, latency=False, exclude=None, tier="balanced"):
    scored=[]
    requires=set(requires or ["text"])
    excluded=set(exclude or [])
    for name,dns,ad in _candidates(snapshot):
        if name in excluded:
            continue
        runtime=ad.get("runtime") or {}
        if runtime and runtime.get("ok") is False:
            continue
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
        preferred=inf.get("preferred_model")
        for m in eligible:
            resident=bool(m.get("resident"))
            size=float(m.get("size") or 10**12)
            expected=_model_expected_ms(m,tier)
            busy_penalty=100000.0 if active else 0.0
            cold_penalty=5000.0 if not resident else 0.0
            network_penalty=120.0 if dns is not None else 0.0
            preferred_bonus=-150.0 if m.get("name")==preferred else 0.0
            # Reflex work strongly rewards small/warm/fast. Deep work rewards model
            # capacity after capability filtering. Balanced work lets measurements,
            # warmth and the user's preferred model dominate.
            if tier=="reflex":
                policy=(size/1e9)*35.0
            elif tier=="deep":
                policy=-(size/1e9)*35.0
            else:
                policy=(size/1e9)*3.0
            score=busy_penalty+cold_penalty+network_penalty+expected+preferred_bonus+policy
            scored.append((score,name,dns,[m]))
    if not scored: raise RuntimeError("Fabric has no worker satisfying this inference request")
    scored.sort(key=lambda x:x[0])
    return scored[0]


def choose_node(base=DEFAULT_NODE, *, model=None, requires=None, latency=False, exclude=None):
    """Choose a worker from one atomic routing snapshot."""
    return _choose_from_snapshot(_nodes(base), model=model, requires=requires,
                                 latency=latency, exclude=exclude, tier=("reflex" if latency else "balanced"))


def _ad_for_target(base, target, snapshot=None):
    # `snapshot` lets one placement decision reuse the same control-plane truth.
    snap=snapshot if snapshot is not None else _nodes(base)
    return _find_target(snap,target)[1]

def infer(messages, *, model=None, requires=None, latency=False, priority="interactive",
          think=False, options=None, timeout=90, base=DEFAULT_NODE, owner="app"):
    snap=_nodes(base)
    tier="reflex" if latency else "balanced"
    score,target,dns,eligible=_choose_from_snapshot(snap,model=model,requires=requires,latency=latency,tier=tier)
    ad=_ad_for_target(base,target,snapshot=snap)
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
      "delivery":{"target":target},"provenance":{},"extensions":{"futurecrash":{"owner":owner,"work_class":tier}},
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
                 base=DEFAULT_NODE, owner="lo", route=None, work_class=None):
    """Route a mature Ollama chat payload to Fabric and yield its JSONL stream.

    A healthy turn remains sticky to one worker/model. Before the first streamed
    event, however, BUSY or transport failure is a placement failure, not a user
    failure: retry once on another eligible worker and update the turn route.
    """
    import socket

    model=payload.get("model") or None
    reqs=set(requires or ["text"])
    decision = work_class or _classify_work(_last_user_text(payload.get("messages")), requires=reqs,
                                            has_images=any(bool(m.get("images")) for m in payload.get("messages",[]) if isinstance(m,dict)),
                                            tool_count=len(payload.get("tools") or []))
    tier = decision.get("tier","balanced") if isinstance(decision,dict) else decision.tier
    tried=set()
    max_attempts=3

    def select(prefer_route=True):
        # One /v1/nodes read per placement attempt. Older code re-fetched the
        # control plane two or three times while choosing one worker, amplifying
        # exactly the pressure a busy Fabric must avoid.
        snap=_nodes(base)
        if prefer_route and isinstance(route,dict) and route.get("target") and route.get("target") not in tried:
            target=str(route["target"]); dns=route.get("dns")
            found_dns,ad=_find_target(snap,target)
            if found_dns is not None:
                dns=found_dns
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
        _,target,dns,eligible=_choose_from_snapshot(snap,model=model,requires=reqs,latency=(tier=="reflex"),exclude=tried,tier=tier)
        ad=_ad_for_target(base,target,snapshot=snap)
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
        # Surface placement before opening the inference stream.  This separates
        # routing time from prompt-evaluation/TTFT in LO telemetry instead of
        # making the first model frame look like a ten-second routing decision.
        yield {"_fabric_meta":"route", "_fabric_node":target, "_fabric_model":chosen}
        inp={"model":chosen,"messages":payload.get("messages") or [],"timeout":timeout,
             "keep_alive":payload.get("keep_alive",-1),"options":payload.get("options") or {}}
        if "think" in payload: inp["think"]=payload.get("think")
        if isinstance(payload.get("tools"),list): inp["tools"]=payload["tools"]
        packet={
          "fabric":"fwp/1","kind":"task","origin":owner,"relationships":{},
          "work":{"operation":"model.infer","objective":"stream conversational inference","input":inp},
          "capabilities":{"requires":list(reqs),"prefers":{"latency":"low" if tier=="reflex" else "normal","work_class":tier}},
          "context":{},"execution":{"priority":priority,"cancellable":True,
            "budget":{"wall_ms":int(timeout*1000)+5000,"child_jobs":0,"depth":0}},
          "authority":{"principal":"user","grants":["model.infer"],"confirmed_operations":[]},
          "delivery":{"target":target},"provenance":{},"extensions":{"futurecrash":{"owner":owner,"work_class":tier}},
        }
        endpoint=(f"https://{dns}:7332" if dns else base.rstrip('/'))+"/v1/infer/stream"
        req=urllib.request.Request(endpoint,data=json.dumps({"packet":packet}).encode(),
                                   headers={"Content-Type":"application/json"},method="POST")
        emitted=False
        try:
            with urllib.request.urlopen(req,timeout=timeout) as response:
                node=response.headers.get("X-Fabric-Node") or target
                for raw in response:
                    if not raw.strip():
                        continue
                    try:
                        event=json.loads(raw)
                    except Exception as exc:
                        preview=raw.decode("utf-8","replace").strip()[:160]
                        raise RuntimeError(f"Fabric stream protocol error from {node}: non-JSON frame {preview!r}") from exc
                    if event.get("_fabric_error"):
                        raise RuntimeError(f"Fabric inference failed on {node}: {event.get('error') or 'stream failed'}")
                    emitted=True
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
        # Give a just-released lease a moment to settle. The next attempt owns
        # the next routing snapshot; do not issue a speculative extra /v1/nodes poll.
        time.sleep(.15)
    if last_error:
        raise RuntimeError(f"Fabric inference unavailable after {len(tried)} worker attempt(s): {last_error}") from None
    raise RuntimeError("Fabric inference unavailable")
