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


_DISCOURSE_PREFIX=re.compile(r"^(?:(?:and|then|now|okay|ok|so)\s+)+",re.I)
_SELF_PREFIX=re.compile(r"^(?:lo|look)\s*[,>:;-]?\s+",re.I)

def normalize_utterance(text: str) -> str:
    """Remove harmless conversational wrappers before deterministic judgment.

    This never rewrites payload content after an intent has been recognized; it
    only peels surface glue such as ``and`` or a self-address such as ``lo``.
    """
    out=" ".join(str(text or "").strip().split())
    previous=None
    while out and out!=previous:
        previous=out
        out=_DISCOURSE_PREFIX.sub("",out).strip()
        out=_SELF_PREFIX.sub("",out).strip()
    return out

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
    normalized=normalize_utterance(text)
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


_REFERENTIAL_ACTIONS={
    "close":"close","dismiss":"close","shut":"close",
    "maximize":"maximize","maximise":"maximize","enlarge":"maximize",
    "fullscreen":"fullscreen","full-screen":"fullscreen",
    "focus":"focus","activate":"focus","raise":"focus","bring":"focus",
    "minimize":"minimize","minimise":"minimize",
}

def _referent_names(ref: Mapping[str,Any]) -> list[str]:
    names=[]
    command=str(ref.get("command") or "").strip()
    if command:
        try: words=shlex.split(command)
        except ValueError: words=command.split()
        if words:
            head=words[0].rsplit("/",1)[-1]
            names.extend([command,head])
    for key in ("name","label","title"):
        if ref.get(key): names.append(str(ref[key]))
    names.extend(str(x) for x in (ref.get("aliases") or []) if str(x).strip())
    out=[]
    for name in names:
        norm=" ".join(name.casefold().split()).strip()
        if norm and norm not in out: out.append(norm)
    return out

def _referent_match(query: str, ref: Mapping[str,Any]) -> float:
    q=" ".join(str(query or "").casefold().split()).strip(" .!?")
    q=re.sub(r"\b(?:the\s+)?(?:window|terminal(?:\s+window)?)\b$","",q).strip()
    if not q: return 0.0
    best=0.0
    for name in _referent_names(ref):
        if q==name: best=max(best,1.0)
        elif len(q)>=3 and name.startswith(q): best=max(best,.97)
        elif len(q)>=4 and q in name: best=max(best,.88)
    return best

def referential_action(text: str, referents):
    """Resolve a narrow action over a recent typed referent or return None.

    This tree decides action + object only. Whether the host can perform that
    action is a separate capability-curation fact supplied at the edge.
    """
    normalized=normalize_utterance(text)
    # Normalize common two-word window phrasing before the compact verb tree.
    normalized=re.sub(r"^(full)\s+screen\b","fullscreen",normalized,flags=re.I)
    m=re.match(r"^(?:please\s+)?(?:(?:can|could|would|will)\s+you\s+)?(close|dismiss|shut|maximi[sz]e|enlarge|fullscreen|full-screen|focus|activate|raise|minimi[sz]e|bring)\s+(?:up\s+|down\s+|to\s+front\s+)?(.+?)\s*[.!?]?\s*$",normalized,re.I)
    if not m: return None
    rawverb=m.group(1).casefold(); verb=_REFERENTIAL_ACTIONS.get(rawverb)
    if not verb: return None
    obj=m.group(2).casefold().strip()
    hint="terminal_window" if re.search(r"\b(window|terminal(?:\s+window)?)\b",obj) else ""
    deictic=bool(re.fullmatch(r"(?:it|that|this|that one|this one|other one|the other one|the window|that window|this window|the terminal|that terminal|this terminal|that terminal window|this terminal window)",obj))
    compatible=[]
    for ref in list(referents or []):
        if not isinstance(ref,Mapping): continue
        kind=str(ref.get("kind") or "")
        if hint and kind!=hint: continue
        if kind not in {"terminal_window"}: continue
        compatible.append(dict(ref))
    unique=[]; seen=set()
    for ref in compatible:
        key=str(ref.get("id") or ref.get("os_window_id") or ref.get("pid") or ref)
        if key in seen: continue
        seen.add(key); unique.append(ref)
    if deictic:
        # Deictic language may resolve against one explicitly salient/current
        # live object even when other compatible objects exist. "Other one" is
        # the inverse relation and is only deterministic when exactly one other
        # compatible object remains.
        salient=[r for r in unique if r.get("_salient") or r.get("_current")]
        if obj in {"other one","the other one"}:
            if len(salient)!=1: return None
            sid=str(salient[0].get("id") or salient[0])
            others=[r for r in unique if str(r.get("id") or r)!=sid]
            if len(others)!=1: return None
            selected=others[0]; steps=[f"verb:{verb}",f"referent:{selected.get('kind','object')}","resolve:other"]
        elif len(salient)==1:
            selected=salient[0]; steps=[f"verb:{verb}",f"referent:{selected.get('kind','object')}","resolve:salient"]
        elif len(unique)==1:
            selected=unique[0]; steps=[f"verb:{verb}",f"referent:{selected.get('kind','object')}","resolve:deictic"]
        else:
            return None
    else:
        scored=sorted(((_referent_match(obj,ref),idx,ref) for idx,ref in enumerate(unique)),key=lambda x:(-x[0],x[1]))
        if not scored or scored[0][0] < .88: return None
        second=scored[1][0] if len(scored)>1 else 0.0
        if second>=scored[0][0]-.08: return None
        selected=scored[0][2]; steps=[f"verb:{verb}",f"referent:{selected.get('kind','object')}",f"resolve:name:{scored[0][0]:.2f}"]
    # JEV bookkeeping is not part of the host object's identity/capability data.
    selected={k:v for k,v in selected.items() if not str(k).startswith("_")}
    return {"kind":"referential_action","verb":rawverb,"action":verb,"object":selected,"confidence":1.0,"steps":steps}

def image_imperative(text: str):
    """Resolve explicit image-generation language before topic words can hijack it.

    The recognized image noun establishes ownership of the remaining description.
    Words such as rain/snow/sun inside that payload are image content, not weather
    requests. Signal/Oracle-specific requests intentionally fall through.
    """
    normalized=normalize_utterance(text)
    low=normalized.casefold()
    if re.search(r"\b(?:signal|oracle)\b",low) and re.search(r"\b(?:image|picture|art|scene)\b",low):
        return None
    patterns=(
        r"^(?:please\s+)?(?:make|generate|create|render|draw)\s+(?:me\s+)?(?:an?\s+)?(?:image|picture|illustration|artwork|photo)\s+(?:of|showing|depicting)\s+(.+?)\s*[.!?]?\s*$",
        r"^(?:please\s+)?(?:make|generate|create|render|draw)\s+(?:me\s+)?(.+?)\s+(?:image|picture|illustration|artwork|photo)\s*[.!?]?\s*$",
    )
    for pattern in patterns:
        m=re.match(pattern,normalized,re.I)
        if not m: continue
        prompt=m.group(1).strip(" .!?")
        if not prompt: return None
        return {"kind":"image_generation","tool":"generate_image","prompt":prompt,"confidence":1.0,
                "steps":["verb:generate","object:image","payload:owned"]}
    return None
