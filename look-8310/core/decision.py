#!/usr/bin/env python3
"""Fabric Decision Plane.

Decision policy is deterministic and authority-bearing; learned workers only
supply bounded judgment evidence. A missing worker must always be cheap to lose.
"""
from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
import uuid
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

PROFILES = {"conservative", "workspace", "power", "unsafe"}
CONSEQUENCES = {"low", "medium", "high", "critical"}
TIMEOUT_ACTIONS = {"continue", "cancel", "defer"}
DEFAULT_DEADLINES = {"conservative": 60, "workspace": 60, "power": 30, "unsafe": 30}
CONFIG_PATH = Path.home()/".config"/"future-crash-look"/"config.json"
DEFAULT_OPENJEV_URL = "http://127.0.0.1:8791"
_CIRCUIT = {"failures": 0, "retry_after": 0.0, "last_error": "", "last_ok": 0.0, "latency_ms": None}


def load_config() -> dict[str, Any]:
    """Read optional user config. Invalid config fails closed to defaults."""
    try:
        raw=json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        return raw if isinstance(raw,dict) else {}
    except Exception:
        return {}


def decision_config() -> dict[str, Any]:
    raw=(load_config().get("decision") or {})
    if not isinstance(raw,dict): raw={}
    enabled=bool(raw.get("enabled", True))
    provider=str(raw.get("provider") or "openjev").strip().lower()
    url=str(raw.get("url") or os.environ.get("FCL_DECISION_URL") or DEFAULT_OPENJEV_URL).rstrip("/")
    mode=str(raw.get("mode") or "live").strip().lower()
    return {"enabled":enabled,"provider":provider,"url":url,"mode":mode}


def probability_margin(probabilities: dict[str, Any]) -> float:
    vals=[]
    for value in (probabilities or {}).values():
        try: vals.append(float(value))
        except (TypeError,ValueError): pass
    vals=sorted(vals,reverse=True)
    return max(0.0, vals[0]-(vals[1] if len(vals)>1 else 0.0)) if vals else 0.0


@dataclass(frozen=True)
class PolicyPlan:
    action: str
    timeout_action: str
    deadline_seconds: int
    reason: str
    requires_confirmation: bool
    def public(self) -> dict[str, Any]: return asdict(self)


def _norm_profile(value: str) -> str:
    value=str(value or "workspace").strip().lower()
    return value if value in PROFILES else "workspace"


def _norm_consequence(value: str) -> str:
    value=str(value or "low").strip().lower()
    return value if value in CONSEQUENCES else "low"


def plan(*, profile: str="workspace", confidence: float=0.0, margin: float|None=None,
         consequence: str="low", reversible: bool=True, deadline_seconds: int|None=None) -> PolicyPlan:
    """Turn uncertainty evidence into authority policy.

    Margin matters because a calibrated decision head may be conservative in its
    absolute confidence while still separating the best candidate clearly.
    """
    profile=_norm_profile(profile); consequence=_norm_consequence(consequence)
    try: confidence=max(0.0,min(1.0,float(confidence)))
    except Exception: confidence=0.0
    try: margin=max(0.0,min(1.0,float(margin))) if margin is not None else 0.0
    except Exception: margin=0.0
    deadline=max(5,min(int(deadline_seconds or DEFAULT_DEADLINES[profile]),3600))
    hard=consequence in {"high","critical"} or not reversible
    if hard:
        return PolicyPlan("ask","cancel",deadline,"consequential or irreversible work requires explicit human confirmation",True)
    # Either explicit model confidence or decisive separation may authorize only
    # low-risk reversible work. This is intentionally not used for consequential work.
    if consequence=="low" and (confidence>=0.90 or (confidence>=0.55 and margin>=0.35)):
        return PolicyPlan("act","continue",deadline,"decision evidence is strong and the action is low-risk/reversible",False)
    if profile in {"power","unsafe"} and consequence=="low":
        return PolicyPlan("ask","continue",deadline,"optional clarification; delegated mode may continue at deadline",False)
    return PolicyPlan("ask","defer",deadline,"clarification is cheaper than speculative work",False)


def new_request(*, question: str, choices: list[dict[str,Any]], profile: str="workspace",
                confidence: float=0.0, margin: float|None=None, consequence: str="low", reversible: bool=True,
                preferred: str|None=None, fallback: str|None=None, deadline_seconds: int|None=None,
                origin: str="local", job_id: str|None=None, channels: list[str]|None=None,
                context: dict[str,Any]|None=None, provider: str="deterministic") -> dict[str,Any]:
    question=" ".join(str(question or "").split())
    if not question: raise ValueError("decision question required")
    if not isinstance(choices,list) or len(choices)<2: raise ValueError("decision requires at least two choices")
    normalized=[]; seen=set()
    for index,raw in enumerate(choices):
        if not isinstance(raw,dict): raw={"value":str(raw)}
        value=str(raw.get("value") or raw.get("id") or index).strip()
        if not value or value in seen: raise ValueError("decision choice values must be unique and non-empty")
        seen.add(value); item=dict(raw); item["value"]=value; item.setdefault("label",value); normalized.append(item)
    policy=plan(profile=profile,confidence=confidence,margin=margin,consequence=consequence,reversible=reversible,deadline_seconds=deadline_seconds)
    now=time.time(); preferred=str(preferred or normalized[0]["value"])
    if preferred not in seen: preferred=normalized[0]["value"]
    if fallback is None: fallback=preferred if policy.timeout_action=="continue" else policy.timeout_action
    fallback=str(fallback)
    if fallback not in seen and fallback not in TIMEOUT_ACTIONS:
        fallback=preferred if policy.timeout_action=="continue" else policy.timeout_action
    return {"schema":"fabric-decision-v1","id":"decision_"+uuid.uuid4().hex,"created":now,
            "expires":now+policy.deadline_seconds,"status":"pending","question":question,"choices":normalized,
            "preferred":preferred,"fallback":fallback,"profile":_norm_profile(profile),
            "confidence":max(0.0,min(1.0,float(confidence or 0.0))),"margin":float(margin or 0.0),
            "consequence":_norm_consequence(consequence),"reversible":bool(reversible),"origin":str(origin or "local"),
            "job_id":str(job_id or "") or None,"channels":list(channels or ["terminal","dash","signal"]),
            "context":dict(context or {}),"provider":str(provider or "deterministic"),"policy":policy.public()}


class OpenJevShadow:
    """OpenJev-compatible worker with bounded failure/backoff.

    The class name is retained for API compatibility; in 5.4 it may run live, but
    authority remains in Decision Plane policy rather than in this HTTP client.
    """
    def __init__(self, base_url: str|None=None, timeout: float=1.5):
        cfg=decision_config()
        self.enabled=bool(cfg["enabled"] and cfg["provider"]=="openjev")
        self.base_url=str(base_url or cfg["url"]).rstrip("/")
        self.timeout=max(0.1,min(float(timeout),10.0))

    def choice(self, *, state: str, question: str, candidates: list[str]) -> dict[str,Any]:
        if not self.enabled: raise RuntimeError("OpenJev decision worker disabled")
        if time.monotonic() < float(_CIRCUIT.get("retry_after") or 0): raise RuntimeError("OpenJev decision worker cooling down")
        labels=[str(x) for x in candidates if str(x)]
        if len(labels)<2: raise ValueError("OpenJev choice needs at least two candidates")
        payload={"state":str(state or "")[:32000],"questions":{"decision":{"type":"choice","instructions":str(question or "Choose the best option."),"criteria":{label:None for label in labels}}}}
        req=urllib.request.Request(self.base_url+"/v1/systemone",data=json.dumps(payload).encode(),headers={"Content-Type":"application/json"})
        started=time.perf_counter()
        with urllib.request.urlopen(req,timeout=self.timeout) as response:
            raw=json.loads(response.read().decode("utf-8","replace") or "{}")
        elapsed=round((time.perf_counter()-started)*1000,2)
        answer=raw.get("answers",{}).get("decision",{}) if isinstance(raw,dict) else {}
        choice=answer.get("choice") if isinstance(answer,dict) else (answer if isinstance(answer,str) else None)
        probabilities=answer.get("probabilities",{}) if isinstance(answer,dict) else {}
        confidence=answer.get("confidence") if isinstance(answer,dict) else None
        if confidence is None and choice is not None and isinstance(probabilities,dict):
            try: confidence=float(probabilities.get(choice))
            except (TypeError,ValueError): confidence=None
        _CIRCUIT.update(failures=0,retry_after=0.0,last_error="",last_ok=time.time(),latency_ms=elapsed)
        return {"ok":True,"provider":"openjev","url":self.base_url,"elapsed_ms":elapsed,"choice":choice,
                "probabilities":probabilities if isinstance(probabilities,dict) else {},"confidence":confidence,
                "margin":probability_margin(probabilities if isinstance(probabilities,dict) else {}),"raw":raw}

    def try_choice(self, **kwargs) -> dict[str,Any]:
        try: return self.choice(**kwargs)
        except urllib.error.HTTPError as exc:
            try: detail=exc.read().decode("utf-8","replace").strip()
            except Exception: detail=""
            result={"ok":False,"provider":"openjev","url":self.base_url,"error":str(exc)}
            if detail:
                try: result["detail"]=json.loads(detail)
                except Exception: result["detail"]=detail
        except (OSError,ValueError,RuntimeError,urllib.error.URLError,TimeoutError) as exc:
            result={"ok":False,"provider":"openjev","url":self.base_url,"error":str(exc)}
        failures=int(_CIRCUIT.get("failures") or 0)+1
        backoff=min(30.0,2.0**min(failures,4))
        _CIRCUIT.update(failures=failures,retry_after=time.monotonic()+backoff,last_error=str(result.get("error") or "error"))
        result["retry_after_seconds"]=backoff
        return result


def provider_status() -> dict[str,Any]:
    cfg=decision_config(); openjev=OpenJevShadow()
    state="disabled" if not openjev.enabled else ("degraded" if _CIRCUIT.get("failures") else "configured")
    return {"provider":cfg["provider"],"enabled":cfg["enabled"],"mode":cfg["mode"],"url":cfg["url"],"state":state,
            "last_ok":_CIRCUIT.get("last_ok") or None,"latency_ms":_CIRCUIT.get("latency_ms"),
            "failures":int(_CIRCUIT.get("failures") or 0),"last_error":_CIRCUIT.get("last_error") or None}
