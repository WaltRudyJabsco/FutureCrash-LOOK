#!/usr/bin/env python3
"""Shared cognition primitives for Future Crash + LOOK.

6.6 deliberately keeps this layer small and inspectable.  It does not replace
LO or become an agent framework.  It turns fuzzy operator language into a
bounded intent/tool neighborhood, creates explicit goal state for a turn, and
provides cheap satisfaction checks after tools run.
"""
from __future__ import annotations

import difflib
import re
import time
import uuid
from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(frozen=True)
class ActionSpec:
    name: str
    family: str
    risk: str
    effect: str
    aliases: tuple[str, ...] = ()


# Names here intentionally match LO's actual tool schema.  Keeping this registry
# independent from presentation lets LOOK, Signal, Albert, and future clients
# reason over the same action vocabulary without duplicating policy.
ACTION_SPECS = (
    ActionSpec("web_search", "web", "read", "observation", ("web search", "search online", "headlines", "news", "latest")),
    ActionSpec("weather", "weather", "read", "observation", ("weather", "forecast", "temperature", "rain", "snow", "wind")),
    ActionSpec("place_lookup", "places", "read", "observation", ("place", "location", "geocode", "where is")),
    ActionSpec("wikipedia", "knowledge", "read", "observation", ("wikipedia", "encyclopedia", "background article")),
    ActionSpec("wikidata", "knowledge", "read", "observation", ("wikidata", "structured facts")),
    ActionSpec("papers", "research", "read", "observation", ("papers", "research paper", "doi", "journal")),
    ActionSpec("archive", "research", "read", "observation", ("archive", "historical artifact", "primary source")),
    ActionSpec("list_files", "files", "read", "observation", ("list files", "show files", "folder contents")),
    ActionSpec("inspect_directory", "files", "read", "observation", ("directory", "folder size", "count files")),
    ActionSpec("read_file", "files", "read", "observation", ("read file", "open file contents", "inspect file")),
    ActionSpec("search_files", "files", "read", "observation", ("find file", "search files", "filename")),
    ActionSpec("search_content", "files", "read", "observation", ("search content", "find text", "grep")),
    ActionSpec("write_file", "files", "local_effect", "mutation", ("write file", "edit file", "save file")),
    ActionSpec("create_text_files", "files", "local_effect", "mutation", ("create files", "make files")),
    ActionSpec("copy_path", "files", "local_effect", "mutation", ("copy", "duplicate", "backup")),
    ActionSpec("move_path", "files", "local_effect", "mutation", ("move", "rename")),
    ActionSpec("remove_path", "files", "destructive", "mutation", ("delete", "remove")),
    ActionSpec("make_directory", "files", "local_effect", "mutation", ("make folder", "create directory")),
    ActionSpec("open_path", "display", "local_effect", "action", ("open file", "launch file", "play file")),
    ActionSpec("preview_path", "display", "local_effect", "action", ("preview", "quick look")),
    ActionSpec("reveal_path", "display", "local_effect", "action", ("reveal", "show in finder", "show in files")),
    ActionSpec("open_url", "browser", "local_effect", "action", ("open website", "open url", "visit", "browser")),
    ActionSpec("media_search", "media", "read", "observation", ("find music", "find movie", "media search")),
    ActionSpec("media_play", "media", "local_effect", "action", ("play", "listen to", "watch")),
    ActionSpec("media_queue", "media", "local_effect", "action", ("queue", "add to queue")),
    ActionSpec("media_control", "media", "local_effect", "action", ("pause", "resume", "next track", "previous track", "stop playback")),
    ActionSpec("audio_speak", "speech", "local_effect", "action", ("say", "speak", "read aloud", "tell me aloud")),
    ActionSpec("game_action", "games", "local_effect", "action", ("game", "chess", "checkers", "backgammon", "tic tac toe", "gtnw")),
    ActionSpec("generate_image", "image", "local_effect", "action", ("generate image", "draw", "render image", "make a picture")),
    ActionSpec("schedule_prompt", "schedule", "external_effect", "action", ("schedule", "remind", "every day", "later")),
    ActionSpec("schedule_list", "schedule", "read", "observation", ("scheduled jobs", "reminders")),
    ActionSpec("list_processes", "system", "read", "observation", ("processes", "what is running", "pid")),
    ActionSpec("listening_ports", "system", "read", "observation", ("port", "listening", "what uses port")),
    ActionSpec("system_snapshot", "system", "read", "observation", ("system status", "machine status", "host status")),
    ActionSpec("run_command", "system", "dangerous", "command", ("run command", "shell", "terminal command")),
)
ACTION_BY_NAME = {spec.name: spec for spec in ACTION_SPECS}
ACTION_IDS = {
    "web_search":"web.search", "weather":"weather.get", "place_lookup":"places.lookup",
    "wikipedia":"knowledge.wikipedia", "wikidata":"knowledge.wikidata",
    "papers":"research.papers", "archive":"research.archive",
    "list_files":"files.list", "inspect_directory":"files.inspect", "read_file":"files.read",
    "search_files":"files.search", "search_content":"files.search_content", "write_file":"files.write",
    "create_text_files":"files.create", "copy_path":"files.copy", "move_path":"files.move",
    "remove_path":"files.remove", "make_directory":"files.mkdir",
    "open_path":"display.open", "preview_path":"display.preview", "reveal_path":"display.reveal",
    "open_url":"browser.open", "media_search":"media.search", "media_play":"media.play",
    "media_queue":"media.queue", "media_control":"media.control", "audio_speak":"audio.speak",
    "game_action":"games.launch", "generate_image":"image.generate",
    "schedule_prompt":"schedule.create", "schedule_list":"schedule.list",
    "list_processes":"system.processes", "listening_ports":"system.ports",
    "system_snapshot":"system.snapshot", "run_command":"system.command",
}

def public_registry() -> list[dict[str,Any]]:
    rows=[]
    for spec in ACTION_SPECS:
        row=asdict(spec); row["id"]=ACTION_IDS.get(spec.name,spec.name.replace("_",".")); row["tool"]=row.pop("name")
        rows.append(row)
    return rows

FAMILY_TOOLS: dict[str, set[str]] = {}
for _spec in ACTION_SPECS:
    FAMILY_TOOLS.setdefault(_spec.family, set()).add(_spec.name)

# Families may need adjacent capabilities to complete a natural request.  These
# are still narrow enough to stop the model wandering into unrelated toolsets.
FAMILY_NEIGHBORS = {
    "web": {"web", "browser", "speech", "display"},
    "weather": {"weather", "speech"},
    "files": {"files", "display", "image"},
    "media": {"media", "speech"},
    "games": {"games"},
    "speech": {"speech"},
    "browser": {"browser", "web"},
    "display": {"display", "files", "browser"},
    "image": {"image", "files", "display"},
    "system": {"system"},
    "schedule": {"schedule"},
    "research": {"research", "web", "knowledge"},
    "places": {"places", "web"},
    "knowledge": {"knowledge", "web"},
}


@dataclass
class Route:
    primary: str = "general"
    families: list[str] = field(default_factory=list)
    confidence: float = 0.0
    margin: float = 0.0
    source: str = "rules"
    reason: str = ""
    allowed_tools: list[str] = field(default_factory=list)
    needs_clarification: bool = False

    def public(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class Goal:
    id: str
    created: float
    request: str
    primary: str
    families: list[str]
    status: str = "active"
    steps: list[dict[str, Any]] = field(default_factory=list)

    def public(self) -> dict[str, Any]:
        return asdict(self)


def _compact(text: str) -> str:
    return " ".join(str(text or "").casefold().replace("-", " ").split())


def _token_set(text: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]+", _compact(text)))


def _score_alias(text: str, alias: str) -> float:
    text=_compact(text); alias=_compact(alias)
    if not text or not alias: return 0.0
    if alias in text: return 0.97
    ta=_token_set(text); aa=_token_set(alias)
    overlap=(len(ta & aa) / max(1, len(aa))) if aa else 0.0
    seq=difflib.SequenceMatcher(None,text,alias).ratio()
    return max(seq*0.82, overlap*0.90)


def _rule_scores(text: str) -> dict[str, float]:
    low=_compact(text)
    scores: dict[str,float] = {}
    def bump(family: str, value: float):
        scores[family]=max(scores.get(family,0.0),value)

    patterns=(
        ("games", r"\b(gtnw|chess|checkers|draughts|backgammon|tic tac toe|ttt|play a game|games?)\b", .995),
        ("weather", r"\b(weather|forecast|temperature|temp|rain(?:ing)?|snow(?:ing)?|wind(?:y)?|humidity|precipitation)\b", .995),
        ("web", r"\b(headlines?|breaking news|latest news|current events?|news today|today'?s news)\b", .995),
        ("media", r"\b(play|queue|shuffle|pause|resume|next track|previous track|now playing|listen to)\b", .82),
        ("speech", r"\b(say|speak|read (?:this|that|it)?\s*aloud|out loud|tell .* aloud)\b", .94),
        ("files", r"\b(file|folder|directory|workspace|codebase|project files?|this folder|search files?|filename)\b", .94),
        ("image", r"\b(generate|draw|render|make)\b.*\b(image|picture|illustration|artwork|photo)\b", .96),
        ("schedule", r"\b(remind|schedule|every day|every morning|every evening|later today|tomorrow at)\b", .94),
        ("system", r"\b(process(?:es)?|pid|port\s*\d*|system status|machine status|what is running)\b", .90),
        ("browser", r"\b(open|visit|launch)\b.*\b(browser|website|site|url|web page)\b", .90),
        ("research", r"\b(doi|research paper|journal article|papers|primary source|archive)\b", .88),
    )
    for family,pattern,value in patterns:
        if re.search(pattern,low): bump(family,value)

    # Fuzzy aliases catch ordinary typos/loose wording without allowing a fuzzy
    # match to become execution authority by itself.
    for spec in ACTION_SPECS:
        for alias in spec.aliases:
            s=_score_alias(low,alias)
            if s>=.72:
                bump(spec.family,min(.91,s))
    return scores


def _openjev_choice(text: str, families: list[str]) -> tuple[str|None,float,float]:
    """Use OpenJev only to break a genuinely ambiguous low-risk route."""
    if len(families)<2: return None,0.0,0.0
    try:
        try:
            from .decision import OpenJevShadow
        except Exception:
            from decision import OpenJevShadow
        result=OpenJevShadow(timeout=.35).try_choice(
            state=f"Operator request: {text[:4000]}",
            question="Which capability family best matches the operator's request?",
            candidates=families[:6],
        )
        if not result.get("ok") or result.get("choice") not in families:
            return None,0.0,0.0
        return str(result.get("choice")), float(result.get("confidence") or 0.0), float(result.get("margin") or 0.0)
    except Exception:
        return None,0.0,0.0


def analyze(text: str, *, use_openjev: bool=True) -> Route:
    scores=_rule_scores(text)
    ranked=sorted(scores.items(),key=lambda kv:kv[1],reverse=True)
    if not ranked:
        return Route(primary="general",families=["general"],confidence=.50,margin=.50,source="rules",
                     reason="no bounded capability family dominated",allowed_tools=[])
    top_family,top=ranked[0]
    second=ranked[1][1] if len(ranked)>1 else 0.0
    margin=max(0.0,top-second)

    # Preserve legitimate compound language. A second strong family is not
    # ambiguity when the request actually names both operations.
    families=[family for family,score in ranked if score>=.80 and score>=top-.22]
    source="rules"
    if use_openjev and len(families)>1 and margin<.10:
        choice,jev_conf,jev_margin=_openjev_choice(text,families)
        if choice:
            top_family=choice
            top=max(top,jev_conf)
            margin=max(margin,jev_margin)
            source="openjev"
    neighborhoods=set()
    for family in families or [top_family]:
        neighborhoods.update(FAMILY_NEIGHBORS.get(family,{family}))
    allowed=sorted({name for family in neighborhoods for name in FAMILY_TOOLS.get(family,set())})
    # Only ask when the language is genuinely ambiguous and no bounded family is
    # strong enough.  A fuzzy match alone is evidence, not authority.
    clarify=top<.72 or (len(families)>1 and margin<.03 and source!="openjev")
    reason=f"{top_family} {top:.2f}; margin {margin:.2f}"
    return Route(primary=top_family,families=families or [top_family],confidence=round(top,3),margin=round(margin,3),
                 source=source,reason=reason,allowed_tools=allowed,needs_clarification=clarify)


def build_plan(request: str, route: Route) -> dict[str,Any]:
    """Build a tiny explicit dependency graph from the bounded route.

    This is execution state, not model chain-of-thought. Each step names a
    capability family and the exact registered actions that are eligible.
    """
    steps=[]
    previous=None
    families=list(route.families or [route.primary])
    for index,family in enumerate(families,1):
        tool_names=sorted(FAMILY_TOOLS.get(family,set()) & set(route.allowed_tools or []))
        step={
            "id":f"step_{index}",
            "family":family,
            "status":"pending",
            "depends_on":[previous] if previous else [],
            "actions":[ACTION_IDS.get(name,name.replace("_",".")) for name in tool_names],
        }
        steps.append(step); previous=step["id"]
    return {"schema":"fabric-plan-v1","request":" ".join(str(request).split())[:4000],
            "primary":route.primary,"steps":steps}


def new_goal(request: str, route: Route) -> Goal:
    plan=build_plan(request,route)
    return Goal(id="goal_"+uuid.uuid4().hex[:16],created=time.time(),request=plan["request"],
                primary=route.primary,families=list(route.families),steps=plan["steps"])


def assess(goal: Goal|dict[str,Any], *, successful_tools: list[str]|None=None, final_text: str="") -> dict[str,Any]:
    """Cheap turn-level satisfaction evidence.

    This is deliberately conservative.  It never certifies an external effect
    merely because prose says it happened; action families require a successful
    tool receipt.  Informational/general turns may be satisfied by a non-empty
    final answer.
    """
    if isinstance(goal,Goal): g=goal.public()
    else: g=dict(goal or {})
    families=list(g.get("families") or [])
    successful=set(successful_tools or [])
    effect_families={"media","speech","games","display","browser","image","schedule","files","system"}
    required_effect=[f for f in families if f in effect_families]
    evidence_families={ACTION_BY_NAME[n].family for n in successful if n in ACTION_BY_NAME}
    missing=[f for f in required_effect if f not in evidence_families]
    if missing:
        return {"satisfied":False,"confidence":0.25,"reason":"missing successful action receipt for "+", ".join(missing)}
    if str(final_text or "").strip() or successful:
        return {"satisfied":True,"confidence":0.90 if successful else 0.72,"reason":"final answer/evidence completed the bounded turn"}
    return {"satisfied":False,"confidence":0.10,"reason":"no final answer or successful tool evidence"}


def resolve_name(query: str, candidates: list[dict[str,Any]], *, keys=("name","label","id")) -> dict[str,Any]:
    """Fuzzy human-name resolver. Returns evidence, never executes anything."""
    q=_compact(query)
    rows=[]
    for item in candidates or []:
        aliases=[]
        for key in keys:
            value=item.get(key) if isinstance(item,dict) else None
            if value: aliases.append(str(value))
        aliases.extend(str(x) for x in (item.get("aliases") or []) if isinstance(item,dict))
        score=max([_score_alias(q,a) for a in aliases] or [0.0])
        rows.append((score,item,aliases))
    rows.sort(key=lambda row:row[0],reverse=True)
    if not rows: return {"status":"no_match","confidence":0.0}
    top=rows[0]; second=rows[1][0] if len(rows)>1 else 0.0
    margin=top[0]-second
    status="resolved" if top[0]>=.78 and margin>=.08 else ("clarify" if top[0]>=.55 else "no_match")
    return {"status":status,"confidence":round(top[0],3),"margin":round(margin,3),"item":top[1] if status!="no_match" else None}

class DecisionPlane:
    """Small façade used by surfaces/tests that want one cognition entry point."""
    def __init__(self, *, use_openjev: bool=True):
        self.use_openjev=bool(use_openjev)

    def route(self, text: str) -> Route:
        return analyze(text,use_openjev=self.use_openjev)

    def goal(self, text: str) -> Goal:
        route=self.route(text)
        return new_goal(text,route)

    def resolve(self, query: str, candidates: list[dict[str,Any]]) -> dict[str,Any]:
        return resolve_name(query,candidates)

    def verify(self, goal: Goal|dict[str,Any], *, successful_tools=None, final_text="") -> dict[str,Any]:
        return assess(goal,successful_tools=list(successful_tools or []),final_text=final_text)
