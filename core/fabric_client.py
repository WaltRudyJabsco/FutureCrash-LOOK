#!/usr/bin/env python3
"""Tiny application-side client for Fabric Work Packets.

Apps request capabilities; this module handles node choice, packet submission and
result waiting. It deliberately contains no application semantics.
"""
from __future__ import annotations
import base64, json, time, urllib.request, urllib.error, uuid

from conductor import classify as _classify_work, last_user_text as _last_user_text
try:
    from .fabric_identity import FabricIdentity
except ImportError:
    from fabric_identity import FabricIdentity

FABRIC_IDENTITY = FabricIdentity()

DEFAULT_NODE = "http://127.0.0.1:7332"

def _open(req, *, url, timeout=5.0):
    """Open a Fabric URL with the authorization and TLS pin for that peer.

    Loopback remains credential-free. Remote Tailcat/Tailscale edges carry the
    paired node credential; Tailcat additionally uses the certificate learned at
    pairing. Keeping this here prevents every application from reimplementing auth.
    """
    kwargs={"timeout":timeout}
    context=FABRIC_IDENTITY.ssl_context_for_url(url) if str(url).lower().startswith("https://") else None
    if context is not None:
        kwargs["context"]=context
    return urllib.request.urlopen(req, **kwargs)


def _json(url, payload=None, timeout=5.0):
    data = None if payload is None else json.dumps(payload).encode()
    headers={"Content-Type":"application/json"}
    headers.update(FABRIC_IDENTITY.auth_headers_for_url(url))
    req = urllib.request.Request(url, data=data, headers=headers)
    with _open(req,url=url,timeout=timeout) as r:
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


def _peer_row(snapshot, target):
    wanted=str(target or "").casefold()
    for peer in snapshot.get("peers") or []:
        ad=peer.get("node") or {}
        names={str(peer.get("name") or "").casefold(),
               str((ad.get("identity") or {}).get("name") or "").casefold()}
        if wanted in names:
            return peer
    return {}


def _endpoint_base(snapshot, target, dns, local_base):
    me=snapshot.get("self") or {}
    me_name=str(me.get("name") or ((me.get("identity") or {}).get("name")) or "").casefold()
    if str(target or "").casefold()==me_name:
        return local_base.rstrip('/')
    peer=_peer_row(snapshot,target)
    if peer.get("url"):
        return str(peer["url"]).rstrip('/')
    for value in peer.get("tailcat_endpoints") or []:
        value=str(value or "").rstrip('/')
        if value:
            return value
    if dns:
        return f"https://{dns}:7332"
    return local_base.rstrip('/')


def _model_expected_ms(model, tier="balanced"):
    q=(model.get("qualification") or {})
    ttft=float(q.get("ttft_ms") or 900.0)
    tok=float(q.get("generation_tok_s") or 0.0)
    # Qualification evidence is intentionally modest.  It nudges placement but
    # never overrides hard capability requirements or availability.
    expected_tokens={"reflex":32.0,"balanced":120.0,"deep":320.0}.get(tier,120.0)
    generation=(expected_tokens/tok*1000.0) if tok>0 else 1200.0
    return ttft+generation

def _benchmark_role_bias(model, tier):
    """Small evidence bonus for the requested role; never overrides hard requirements."""
    b=model.get("benchmark") or {}
    fit=str(b.get("fit") or "").upper()
    reasoning=int(b.get("reasoning") or 0) if isinstance(b.get("reasoning"),(int,float)) else 0
    tools=int(b.get("tools") or 0) if isinstance(b.get("tools"),(int,float)) else 0
    agent=bool(b.get("agent")); exact=bool(b.get("exact"))
    if tier=="reflex":
        return -(350.0 if exact else 0.0) -(100.0 if fit=="EXCELLENT" else 0.0)
    if tier=="deep":
        return -(reasoning*220.0) -(tools*70.0) -(180.0 if agent else 0.0)
    return -(reasoning*80.0) -(tools*60.0) -(120.0 if agent else 0.0) -(80.0 if fit in {"GOOD","EXCELLENT"} else 0.0)


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
            evidence_bias=_benchmark_role_bias(m,tier)
            score=busy_penalty+cold_penalty+network_penalty+expected+preferred_bonus+policy+evidence_bias
            scored.append((score,name,dns,[m]))
    if not scored: raise RuntimeError("Fabric has no worker satisfying this inference request")
    scored.sort(key=lambda x:x[0])
    return scored[0]



def explain_route(*, tier="balanced", model=None, requires=None, base=DEFAULT_NODE):
    """Explain one Fabric inference placement using the exact routing evidence.

    This is diagnostic only: it never submits work or changes residency.
    """
    tier=tier if tier in {"reflex","balanced","deep"} else "balanced"
    snap=_nodes(base)
    requires=set(requires or ["text"])
    rows=[]
    for name,dns,ad in _candidates(snap):
        runtime=ad.get("runtime") or {}; inf=ad.get("inference") or {}; models=inf.get("models") or []
        active=(ad.get("supervisor") or {}).get("active")
        preferred=inf.get("preferred_model")
        for m in models:
            f=m.get("features") or {}
            reasons=[]
            if model and m.get("name") != model: reasons.append("model mismatch")
            missing=[r for r in requires if r in {"vision","tools","thinking","embedding"} and not f.get(r)]
            if missing: reasons.append("missing "+",".join(sorted(missing)))
            resident=bool(m.get("resident")); size=float(m.get("size") or 10**12)
            expected=_model_expected_ms(m,tier)
            busy_penalty=100000.0 if active else 0.0
            cold_penalty=5000.0 if not resident else 0.0
            network_penalty=120.0 if dns is not None else 0.0
            preferred_bonus=-150.0 if m.get("name")==preferred else 0.0
            policy=(size/1e9)*35.0 if tier=="reflex" else (-(size/1e9)*35.0 if tier=="deep" else (size/1e9)*3.0)
            evidence_bias=_benchmark_role_bias(m,tier)
            score=busy_penalty+cold_penalty+network_penalty+expected+preferred_bonus+policy+evidence_bias
            rows.append({"node":name,"model":m.get("name"),"eligible":not reasons,"reasons":reasons,
                         "resident":resident,"preferred":m.get("name")==preferred,"busy":bool(active),
                         "expected_ms":round(expected,1),"score":round(score,1),
                         "qualification":m.get("qualification"),"benchmark":m.get("benchmark"),
                         "size":int(m.get("size") or 0)})
    eligible=[r for r in rows if r["eligible"]]
    eligible.sort(key=lambda r:r["score"]); selected=eligible[0] if eligible else None
    return {"tier":tier,"requires":sorted(requires),"selected":selected,"candidates":sorted(rows,key=lambda r:(not r["eligible"],r["score"]))}

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
    pollbase=_endpoint_base(snap,target,dns,base)
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

def _stage_image_artifacts(payload, endpoint):
    """Move Ollama image blobs out of the work packet and into Fabric artifacts.

    Packets are control-plane contracts. Pixel data travels on the artifact path so
    vision requests stay small and remote workers receive the image exactly once.
    """
    messages=[]
    staged=[]
    for message in payload.get("messages") or []:
        if not isinstance(message,dict):
            messages.append(message); continue
        copy=dict(message)
        images=copy.pop("images",None)
        refs=[]
        for index,encoded in enumerate(images or []):
            if not isinstance(encoded,str) or not encoded:
                continue
            result=_json(endpoint.rstrip("/")+"/v1/artifacts", {
                "base64":encoded,
                "media_type":"image/png",
                "name":f"lo-vision-{index+1}.png",
            }, timeout=20.0)
            meta=result.get("artifact") or {}
            digest=meta.get("digest")
            if not digest:
                raise RuntimeError("Fabric artifact staging returned no digest")
            refs.append(digest); staged.append(digest)
        if refs:
            copy["image_artifacts"]=refs
        messages.append(copy)
    return messages,staged

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
                return target,dns,chosen,snap
        _,target,dns,eligible=_choose_from_snapshot(snap,model=model,requires=reqs,latency=(tier=="reflex"),exclude=tried,tier=tier)
        ad=_ad_for_target(base,target,snapshot=snap)
        chosen=model
        if not chosen:
            preferred=((ad.get("inference") or {}).get("preferred_model"))
            names={m.get("name") for m in eligible}
            chosen=preferred if preferred in names else max(eligible,key=lambda m:int(m.get("size") or 0)).get("name")
        return target,dns,chosen,snap

    last_error=None
    attempt_no=0
    busy_grace_deadline=None
    busy_retry_seconds=.35
    # BUSY is temporary capacity pressure, not capability failure. Interactive
    # work gets a short bounded grace period after distinct workers have raced
    # busy; background work still fails fast so it never crowds human requests.
    busy_grace_seconds=min(8.0,max(2.0,float(timeout)*.08)) if priority != "background" else 0.0

    while attempt_no < max_attempts or (busy_grace_deadline and time.monotonic() < busy_grace_deadline):
        if attempt_no >= max_attempts:
            tried.clear()
            attempt_no=0
            time.sleep(busy_retry_seconds)
        try:
            target,dns,chosen,snap=select(prefer_route=(attempt_no==0 and busy_grace_deadline is None))
        except (urllib.error.URLError, TimeoutError, socket.timeout) as exc:
            # Route discovery is control-plane work. A transient slow /v1/nodes
            # response should not leak a raw urllib timeout into LO.
            last_error=exc
            attempt_no += 1
            time.sleep(.15)
            continue
        except RuntimeError as exc:
            # All currently eligible workers may be in the exclusion set. During
            # the interactive BUSY grace window, clear it and ask a fresh snapshot.
            last_error=exc
            if busy_grace_deadline and time.monotonic() < busy_grace_deadline:
                tried.clear(); attempt_no=0
                time.sleep(busy_retry_seconds)
                continue
            break
        if isinstance(route,dict):
            route.update({"target":target,"dns":dns,"model":chosen})
        # Surface placement before opening the inference stream. This separates
        # routing time from prompt-evaluation/TTFT in LO telemetry instead of
        # making the first model frame look like a ten-second routing decision.
        yield {"_fabric_meta":"route", "_fabric_node":target, "_fabric_model":chosen}
        endpoint_base=_endpoint_base(snap,target,dns,base)
        staged_messages,_staged=_stage_image_artifacts(payload, endpoint_base) if any(
            bool(m.get("images")) for m in payload.get("messages",[]) if isinstance(m,dict)
        ) else (payload.get("messages") or [],[])
        inp={"model":chosen,"messages":staged_messages,"timeout":timeout,
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
        endpoint=endpoint_base+"/v1/infer/stream"
        headers={"Content-Type":"application/json"}
        headers.update(FABRIC_IDENTITY.auth_headers_for_url(endpoint))
        req=urllib.request.Request(endpoint,data=json.dumps({"packet":packet}).encode(),
                                   headers=headers,method="POST")
        emitted=False
        try:
            with _open(req,url=endpoint,timeout=timeout) as response:
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
            # 409 before streaming is temporary placement pressure. Try distinct
            # workers first, then briefly wait/re-route instead of telling the user
            # the Fabric is unavailable merely because every lane was busy now.
            if exc.code != 409 or emitted:
                raise last_error from None
            if busy_grace_seconds and busy_grace_deadline is None:
                busy_grace_deadline=time.monotonic()+busy_grace_seconds
        except (urllib.error.URLError, TimeoutError, socket.timeout) as exc:
            last_error=exc
            if emitted:
                raise
        tried.add(target)
        attempt_no += 1
        if isinstance(route,dict):
            route.clear()
        time.sleep(.15)
    if last_error:
        raise RuntimeError(f"Fabric inference unavailable after {len(tried)} worker attempt(s): {last_error}") from None
    raise RuntimeError("Fabric inference unavailable")
