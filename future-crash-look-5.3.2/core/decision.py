#!/usr/bin/env python3
"""Decision control plane for the Future Crash Fabric.

The important distinction is between *deciding* and *acting*.
A DecisionRequest concentrates uncertainty into a tiny object that any trusted
Fabric surface can answer. Jobs may continue, cancel, or defer at the deadline;
no terminal/UI is allowed to become a structural lock on useful work.

This module is deliberately pure except for the optional OpenJev HTTP adapter.
Policy stays inspectable and deterministic even when a learned decision worker is
available in shadow mode.
"""
from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
import uuid
from dataclasses import asdict, dataclass
from typing import Any

PROFILES = {"conservative", "workspace", "power", "unsafe"}
CONSEQUENCES = {"low", "medium", "high", "critical"}
TIMEOUT_ACTIONS = {"continue", "cancel", "defer"}

# A small request deserves a small answer. These defaults are policy, not magic
# sprinkled through renderers or callers.
DEFAULT_DEADLINES = {
    "conservative": 60,
    "workspace": 60,
    "power": 30,
    "unsafe": 30,
}


@dataclass(frozen=True)
class PolicyPlan:
    action: str                 # act | ask | think_more | abort
    timeout_action: str         # continue | cancel | defer
    deadline_seconds: int
    reason: str
    requires_confirmation: bool

    def public(self) -> dict[str, Any]:
        return asdict(self)


def _norm_profile(value: str) -> str:
    value = str(value or "workspace").strip().lower()
    return value if value in PROFILES else "workspace"


def _norm_consequence(value: str) -> str:
    value = str(value or "low").strip().lower()
    return value if value in CONSEQUENCES else "low"


def plan(*, profile: str = "workspace", confidence: float = 0.0,
         consequence: str = "low", reversible: bool = True,
         deadline_seconds: int | None = None) -> PolicyPlan:
    """Choose what to do with uncertainty without performing any work.

    High-consequence or irreversible work never auto-continues. Power/Unsafe
    may continue after silence only for low-consequence reversible work.
    """
    profile = _norm_profile(profile)
    consequence = _norm_consequence(consequence)
    try:
        confidence = max(0.0, min(1.0, float(confidence)))
    except Exception:
        confidence = 0.0
    deadline = int(deadline_seconds or DEFAULT_DEADLINES[profile])
    deadline = max(5, min(deadline, 3600))

    hard_confirmation = consequence in {"high", "critical"} or not reversible
    if hard_confirmation:
        return PolicyPlan(
            action="ask", timeout_action="cancel", deadline_seconds=deadline,
            reason="consequential or irreversible work requires explicit human confirmation",
            requires_confirmation=True,
        )

    if confidence >= 0.90 and consequence == "low":
        return PolicyPlan(
            action="act", timeout_action="continue", deadline_seconds=deadline,
            reason="high-confidence low-consequence reversible decision",
            requires_confirmation=False,
        )

    if profile in {"power", "unsafe"} and consequence == "low":
        return PolicyPlan(
            action="ask", timeout_action="continue", deadline_seconds=deadline,
            reason="optional human clarification; delegated mode may continue at the deadline",
            requires_confirmation=False,
        )

    # Workspace/Conservative deliberately fail cheap: preserve state and let the
    # operator collapse uncertainty rather than silently choosing a weak guess.
    return PolicyPlan(
        action="ask", timeout_action="defer", deadline_seconds=deadline,
        reason="clarification is cheaper than speculative work",
        requires_confirmation=False,
    )


def new_request(*, question: str, choices: list[dict[str, Any]], profile: str = "workspace",
                confidence: float = 0.0, consequence: str = "low", reversible: bool = True,
                preferred: str | None = None, fallback: str | None = None,
                deadline_seconds: int | None = None, origin: str = "local",
                job_id: str | None = None, channels: list[str] | None = None,
                context: dict[str, Any] | None = None, provider: str = "deterministic") -> dict[str, Any]:
    """Build a portable DecisionRequest suitable for persistence or transport."""
    question = " ".join(str(question or "").split())
    if not question:
        raise ValueError("decision question required")
    if not isinstance(choices, list) or len(choices) < 2:
        raise ValueError("decision requires at least two choices")
    normalized = []
    seen = set()
    for index, raw in enumerate(choices):
        if not isinstance(raw, dict):
            raw = {"value": str(raw)}
        value = str(raw.get("value") or raw.get("id") or index).strip()
        if not value or value in seen:
            raise ValueError("decision choice values must be unique and non-empty")
        seen.add(value)
        item = dict(raw)
        item["value"] = value
        item.setdefault("label", value)
        normalized.append(item)

    policy = plan(profile=profile, confidence=confidence, consequence=consequence,
                  reversible=reversible, deadline_seconds=deadline_seconds)
    now = time.time()
    preferred = str(preferred or normalized[0]["value"])
    if preferred not in seen:
        preferred = normalized[0]["value"]
    if fallback is None:
        fallback = preferred if policy.timeout_action == "continue" else policy.timeout_action
    fallback = str(fallback)
    if fallback not in seen and fallback not in TIMEOUT_ACTIONS:
        fallback = preferred if policy.timeout_action == "continue" else policy.timeout_action

    return {
        "schema": "fabric-decision-v1",
        "id": "decision_" + uuid.uuid4().hex,
        "created": now,
        "expires": now + policy.deadline_seconds,
        "status": "pending",
        "question": question,
        "choices": normalized,
        "preferred": preferred,
        "fallback": fallback,
        "profile": _norm_profile(profile),
        "confidence": max(0.0, min(1.0, float(confidence or 0.0))),
        "consequence": _norm_consequence(consequence),
        "reversible": bool(reversible),
        "origin": str(origin or "local"),
        "job_id": str(job_id or "") or None,
        "channels": list(channels or ["terminal", "dash", "signal"]),
        "context": dict(context or {}),
        "provider": str(provider or "deterministic"),
        "policy": policy.public(),
    }


class OpenJevShadow:
    """Optional OpenJev-compatible decision client.

    Nothing here installs or owns a model. If an OpenJev-compatible service is
    running, Fabric can compare its answer with the deterministic Conductor.
    Failure is silent evidence, never a dependency of normal operation.
    """
    def __init__(self, base_url: str | None = None, timeout: float = 1.5):
        self.base_url = str(base_url or os.environ.get("FCL_DECISION_URL") or "http://127.0.0.1:3000").rstrip("/")
        self.timeout = max(0.1, min(float(timeout), 10.0))

    def choice(self, *, state: str, question: str, candidates: list[str]) -> dict[str, Any]:
        labels = [str(x) for x in candidates if str(x)]
        if len(labels) < 2:
            raise ValueError("OpenJev choice needs at least two candidates")
        payload = {
            "state": str(state or "")[:32000],
            "questions": {
                "decision": {
                    "type": "choice",
                    "instructions": str(question or "Choose the best option."),
                    "criteria": {label: None for label in labels},
                }
            },
        }
        req = urllib.request.Request(
            self.base_url + "/v1/systemone",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )
        started = time.perf_counter()
        with urllib.request.urlopen(req, timeout=self.timeout) as response:
            raw = json.loads(response.read().decode("utf-8", "replace") or "{}")

        # OpenJev-compatible servers return typed answers keyed by our question id.
        # Normalize the useful fields so callers never have to understand a specific
        # server's response envelope; preserve raw for experiments/provenance.
        answer = raw.get("answers", {}).get("decision", {}) if isinstance(raw, dict) else {}
        choice = answer.get("choice") if isinstance(answer, dict) else None
        probabilities = answer.get("probabilities", {}) if isinstance(answer, dict) else {}
        confidence = answer.get("confidence") if isinstance(answer, dict) else None
        if choice is None and isinstance(answer, str):
            choice = answer
        if confidence is None and choice is not None and isinstance(probabilities, dict):
            try:
                confidence = float(probabilities.get(choice))
            except (TypeError, ValueError):
                confidence = None

        return {
            "ok": True,
            "provider": "openjev",
            "url": self.base_url,
            "elapsed_ms": round((time.perf_counter() - started) * 1000, 2),
            "choice": choice,
            "probabilities": probabilities if isinstance(probabilities, dict) else {},
            "confidence": confidence,
            "raw": raw,
        }

    def try_choice(self, **kwargs) -> dict[str, Any]:
        try:
            return self.choice(**kwargs)
        except urllib.error.HTTPError as exc:
            # Preserve the provider's validation detail. A 4xx from a decision
            # worker is actionable protocol evidence, not just "HTTP Error 422".
            try:
                detail = exc.read().decode("utf-8", "replace").strip()
            except Exception:
                detail = ""
            result = {"ok": False, "provider": "openjev", "url": self.base_url, "error": str(exc)}
            if detail:
                try:
                    result["detail"] = json.loads(detail)
                except Exception:
                    result["detail"] = detail
            return result
        except (OSError, ValueError, urllib.error.URLError, TimeoutError) as exc:
            return {"ok": False, "provider": "openjev", "url": self.base_url, "error": str(exc)}
