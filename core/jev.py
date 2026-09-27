"""JEV: tiny deterministic judgment trees for obvious operator intent.

JEV does not execute actions and does not pretend to understand arbitrary prose.
Each tree consumes a small, explicit vocabulary, records the decisions it made,
and returns None when ambiguity belongs to cognition.
"""
from __future__ import annotations

import re
import shlex
from typing import Callable, Mapping, Any

COMMAND_VERBS={"run","launch","execute","start"}

# Suffixes are semantic host modifiers, never argv.  Order is intentionally
# irrelevant: the parser peels them repeatedly until no known modifier remains.
_COMMAND_SUFFIXES=(
    (re.compile(r"\s+(?:again|one more time)\s*$",re.I),"retry"),
    (re.compile(r"\s+(?:in|inside|on)\s+(?:a\s+)?(?:new|another|separate)\s+terminal(?:\s+window)?\s*$",re.I),"terminal:new"),
    (re.compile(r"\s+(?:in|inside|on|from)\s+(?:the\s+)?terminal\s*$",re.I),"terminal:current"),
    (re.compile(r"\s+interactively\s*$",re.I),"terminal:current"),
)


def command_imperative(
    text: str,
    *,
    head_resolves: Callable[[str], bool] | None = None,
    prior: Mapping[str,Any] | None = None,
):
    """Resolve a narrow RUN/LAUNCH imperative or return None.

    Decision tree:
      - explicit verb required;
      - peel known execution modifiers;
      - one command token is sufficient evidence;
      - multi-token payload requires a resolvable executable head;
      - unknown multi-word language falls through to cognition.

    `head_resolves` is supplied by the host edge so this module remains free of
    filesystem/PATH policy. `prior` may preserve presentation mode for AGAIN,
    but never carries authority; the caller must re-check current policy.
    """
    normalized=" ".join(str(text or "").strip().split())
    match=re.match(r"^(?:please\s+)?(run|launch|execute|start)\s+(.+?)\s*[.!]?\s*$",normalized,re.I)
    if not match:
        return None

    verb=match.group(1).casefold()
    payload=match.group(2).strip()
    retry=False
    terminal="current" if verb=="launch" else "none"
    steps=[f"verb:{verb}"]

    changed=True
    while changed and payload:
        changed=False
        for pattern,meaning in _COMMAND_SUFFIXES:
            stripped=pattern.sub("",payload).strip()
            if stripped==payload:
                continue
            payload=stripped; changed=True; steps.append(f"modifier:{meaning}")
            if meaning=="retry": retry=True
            elif meaning.startswith("terminal:"): terminal=meaning.split(":",1)[1]
            break

    if not payload or re.fullmatch(r"(?i)(it|that|this)",payload):
        return None

    try:
        words=shlex.split(payload)
    except ValueError:
        return None
    if not words:
        return None

    resolver=head_resolves or (lambda _head: False)
    if len(words)>1 and not resolver(words[0]):
        return None
    steps.append("payload:single-token" if len(words)==1 else "payload:resolved-head")

    prior=dict(prior or {})
    same_prior=str(prior.get("command") or "")==payload
    if retry and same_prior and terminal=="none":
        if prior.get("new_terminal"):
            terminal="new"; steps.append("inherit:terminal:new")
        elif prior.get("interactive"):
            terminal="current"; steps.append("inherit:terminal:current")

    return {
        "kind":"command",
        "command":payload,
        "verb":verb,
        "retry":retry,
        "terminal":terminal,
        "tokens":len(words),
        "confidence":1.0 if len(words)==1 else 0.98,
        "steps":steps,
    }


_CLOSE_VERBS={"close","dismiss","shut"}

def referential_action(text: str, referents):
    """Resolve a narrow action over a recent typed referent or return None.

    The tree intentionally understands only deictic continuity such as
    "close that window" / "close it".  It never guesses when zero or multiple
    compatible referents exist.
    """
    normalized=" ".join(str(text or "").strip().split())
    m=re.match(r"^(?:please\s+)?(?:(?:can|could|would|will)\s+you\s+)?(close|dismiss|shut)\s+(?:down\s+)?(.+?)\s*[.!?]?\s*$",normalized,re.I)
    if not m:
        return None
    verb=m.group(1).casefold(); obj=m.group(2).casefold().strip()
    hint=""
    if re.search(r"\b(window|terminal(?:\s+window)?)\b",obj): hint="terminal_window"
    deictic=bool(re.fullmatch(r"(?:it|that|this|that one|this one|the window|that window|this window|the terminal|that terminal|this terminal|that terminal window|this terminal window)",obj))
    if not deictic and not hint:
        return None
    candidates=[]
    for ref in list(referents or []):
        if not isinstance(ref,Mapping): continue
        kind=str(ref.get("kind") or "")
        if hint and kind!=hint: continue
        if kind not in {"terminal_window"}: continue
        candidates.append(dict(ref))
    # Preserve caller recency order while deduplicating durable/ephemeral copies.
    unique=[]; seen=set()
    for ref in candidates:
        key=str(ref.get("id") or ref.get("os_window_id") or ref.get("pid") or ref)
        if key in seen: continue
        seen.add(key); unique.append(ref)
    if len(unique)!=1:
        return None
    return {"kind":"referential_action","verb":verb,"action":"close","object":unique[0],"confidence":1.0,"steps":[f"verb:{verb}",f"referent:{unique[0].get('kind','object')}"]}
