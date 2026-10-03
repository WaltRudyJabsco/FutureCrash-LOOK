#!/usr/bin/env python3
"""Fast deterministic work classifier for the Future Crash Fabric.

The conductor is intentionally not another LLM call.  Most turns can be placed
from facts we already have (capabilities, prompt shape, residency and measured
latency).  An optional semantic/reflex model can be added later for ambiguous
work without putting an extra model round-trip in front of every keystroke.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, asdict

_DEEP = re.compile(r"\b(analy[sz]e|architecture|debug|diagnos|refactor|implement|write code|review code|compare|reason|prove|derive|research|investigate|plan|design|why does|trade[- ]?off|optimi[sz]e)\b", re.I)
_REFLEX = re.compile(r"^(hi|hello|hey|thanks|thank you|ping|status|pwd|whoami|date|time|list|show|where is|what is)\b", re.I)
_CODE = re.compile(r"```|\b(traceback|exception|stack trace|segfault|function|class|def |const |let |git diff|systemd|sqlite|http|json|python|javascript|typescript|rust|shell|bash|zsh)\b", re.I)

@dataclass(frozen=True)
class Decision:
    tier: str
    reason: str
    latency_bias: bool
    quality_bias: bool

    def public(self):
        return asdict(self)


def classify(text: str, *, requires=None, has_images=False, tool_count=0) -> Decision:
    """Classify one user turn in microseconds; never performs I/O."""
    text = (text or "").strip()
    requires = set(requires or ())
    words = len(text.split())

    # Hard modalities deserve a capable worker before speed preferences matter.
    if has_images or "vision" in requires:
        return Decision("deep", "vision work", False, True)
    if "thinking" in requires:
        return Decision("deep", "explicit reasoning", False, True)

    # Long/code-heavy/architectural requests benefit from the strongest eligible
    # worker.  This is deliberately conservative: quality failures cost more than
    # the few hundred ms saved by an undersized model.
    if words >= 90 or _CODE.search(text) or _DEEP.search(text):
        return Decision("deep", "complex or code-heavy turn", False, True)

    # Tiny conversational/inspection turns are where a warm small model shines.
    # Tool presence alone does not force a large model; capability filtering still
    # guarantees that the selected model actually declares tool support.
    if words <= 24 and (_REFLEX.search(text) or words <= 8):
        return Decision("reflex", "short interactive turn", True, False)

    return Decision("balanced", "ordinary conversational turn", True, True)


def last_user_text(messages) -> str:
    for message in reversed(messages or []):
        if isinstance(message, dict) and message.get("role") == "user":
            content = message.get("content")
            if isinstance(content, str):
                return content
            if isinstance(content, list):
                return " ".join(str(x.get("text") or "") for x in content if isinstance(x, dict))
    return ""
