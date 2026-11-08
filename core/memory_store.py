#!/usr/bin/env python3
"""Tiny replicated Fabric memory store.

Shared/persona scopes are safe to replicate across the user's trusted Fabric.
Node scope is intentionally local. The store is boring JSON so it remains
inspectable and recoverable without the daemon.
"""
from __future__ import annotations

import hashlib
import fcntl
import functools
import uuid
import json
import os
import socket
import time
from pathlib import Path

VERSION = 3
MAX_ITEMS = 2048
MAX_ATOMS = 4096
MAX_TEXT = 1200


def default_path() -> Path:
    return Path.home() / ".local" / "share" / "look" / "fabric_memory.json"


def node_name() -> str:
    return os.environ.get("FCL_NODE_NAME", "").strip() or socket.gethostname().split(".")[0]


def _empty() -> dict:
    return {"version": VERSION, "items": [], "atoms": []}


def _clean_text(text: str) -> str:
    return " ".join(str(text or "").split())[:MAX_TEXT].strip()


def _valid_scope(scope: str) -> bool:
    return scope == "shared" or scope.startswith("persona:") or scope.startswith("node:")


def _item_id(scope: str, text: str) -> str:
    raw = (scope + "\0" + text.casefold()).encode("utf-8", "replace")
    return hashlib.sha256(raw).hexdigest()[:20]



def _transaction(method):
    @functools.wraps(method)
    def locked(self, *args, **kwargs):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with open(str(self.path) + '.lock', 'a') as lock:
            os.chmod(lock.name, 0o600)
            fcntl.flock(lock, fcntl.LOCK_EX)
            return method(self, *args, **kwargs)
    return locked


def _provenance(row):
    return {'superseded_hashes': [str(x) for x in row.get('superseded_hashes',[]) if isinstance(x,str) and len(x)==64][-64:],
            'deleted': bool(row.get('deleted', False)), 'evidence': str(row.get('evidence') or '')[:1200],
            'source': str(row.get('source') or '')[:120],
            'revision': max(1, int(row.get('revision') or 1)),
            'previous_text': str(row.get('previous_text') or '')[:1200]}

class FabricMemory:
    def __init__(self, path: Path | str | None = None):
        self.path = Path(path or default_path())

    def load(self) -> dict:
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            if not isinstance(data, dict):
                return _empty()
            items = data.get("items") if isinstance(data.get("items"), list) else []
            clean = []
            for row in items:
                if not isinstance(row, dict):
                    continue
                scope = str(row.get("scope") or "")
                text = _clean_text(row.get("text") or "")
                if (not text and not (row.get("deleted") and row.get("id"))) or not _valid_scope(scope):
                    continue
                clean.append({
                    "id": str(row.get("id") or _item_id(scope, text)),
                    "scope": scope,
                    "text": text,
                    "importance": max(1, min(100, int(row.get("importance") or 60))),
                    "created_at": float(row.get("created_at") or time.time()),
                    "updated_at": float(row.get("updated_at") or row.get("created_at") or time.time()),
                    "source_node": str(row.get("source_node") or "unknown")[:128],
                    **_provenance(row),
                })
            clean.sort(key=lambda x: (x["updated_at"], x["importance"]))
            atoms=[]
            for row in data.get("atoms") or []:
                if not isinstance(row,dict): continue
                scope=str(row.get("scope") or "shared").strip().lower()
                if not _valid_scope(scope): continue
                subject=_clean_text(row.get("s") or row.get("subject") or "")[:180]
                value=_clean_text(row.get("v") or row.get("value") or "")[:360]
                if not (subject or value): continue
                atom={"id":str(row.get("id") or _item_id(scope, "|".join([str(row.get("k") or "fact"),subject,str(row.get("r") or ""),value]))),
                      "scope":scope,"k":str(row.get("k") or "fact")[:32],"s":subject,
                      "r":_clean_text(row.get("r") or row.get("relation") or "")[:80],"v":value,
                      "c":max(1,min(100,int(row.get("c",row.get("confidence",70)) or 70))),
                      "u":max(1,int(row.get("u",row.get("uses",1)) or 1)),
                      "updated_at":float(row.get("updated_at") or row.get("t") or time.time()),
                      "source_node":str(row.get("source_node") or "unknown")[:128]}
                atoms.append(atom)
            atoms.sort(key=lambda x:(x["updated_at"],x["c"],x["u"]))
            return {"version": VERSION, "items": clean[-MAX_ITEMS:], "atoms": atoms[-MAX_ATOMS:]}
        except Exception:
            return _empty()

    def save(self, data: dict) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_name(self.path.name + "." + uuid.uuid4().hex + ".tmp")
        tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        try:
            os.chmod(tmp, 0o600)
        except OSError:
            pass
        tmp.replace(self.path)
        try:
            os.chmod(self.path, 0o600)
        except OSError:
            pass

    @_transaction
    def forget(self, fragment):
        data=self.load()
        count=0
        for row in data['items']:
            if row['scope']=='shared' and not row.get('deleted') and fragment.casefold() in row['text'].casefold():
                hashes=list(row.get('superseded_hashes',[]))
                hashes.append(hashlib.sha256(row['text'].encode()).hexdigest())
                row.update(superseded_hashes=list(dict.fromkeys(hashes))[-64:],text='',evidence='',previous_text='',deleted=True,
                           updated_at=time.time(),source_node=node_name(),
                           revision=int(row.get('revision',1))+1)
                count+=1
        self.save(data)
        return count

    @_transaction
    def remember(self, text, importance=70, *, target_id=None, evidence, source, expected_updated_at=None):
        data = self.load()
        old = next((r for r in data['items'] if r['id'] == target_id and r['scope'] == 'shared'), None)
        if target_id and old is None:
            raise ValueError('unknown shared memory record')
        if old and expected_updated_at is not None and old['updated_at'] != expected_updated_at:
            raise ValueError('shared memory changed during reconciliation; retry')
        text = _clean_text(text)
        if not text or not evidence:
            raise ValueError('user memory requires text and evidence')
        iid = target_id or _item_id('shared', text)
        if old is None:
            old = next((r for r in data['items'] if r['id'] == iid), None)
        now = time.time()
        item = dict(old or {}, id=iid, scope='shared', text=text, deleted=False,
                    importance=max(1, min(100, importance)),
                    created_at=old['created_at'] if old else now,
                    updated_at=now, source_node=node_name(), evidence=evidence[:1200],
                    source=source[:120], revision=int((old or {}).get('revision', 0)) + 1,
                    previous_text=old['text'] if old and old['text'] != text else (old or {}).get('previous_text', ''))
        hashes=list((old or {}).get('superseded_hashes',[]))
        if old and old['text'] and old['text']!=text:
            hashes.append(hashlib.sha256(old['text'].encode()).hexdigest())
        item['superseded_hashes']=list(dict.fromkeys(hashes))[-64:]
        data['items'] = [r for r in data['items'] if r['id'] != iid] + [item]
        self.save(data)
        return dict(item)

    @_transaction
    def add(self, scope: str, text: str, importance: int = 60, source_node: str | None = None) -> dict:
        scope = str(scope or "").strip().lower()
        text = _clean_text(text)
        if not _valid_scope(scope):
            raise ValueError("scope must be shared, persona:<name>, or node:<name>")
        if not text:
            raise ValueError("memory text required")
        now = time.time()
        data = self.load()
        iid = _item_id(scope, text)
        found = None
        for item in data["items"]:
            if item.get("id") == iid:
                found = item
                break
        if found:
            found["importance"] = max(int(found.get("importance") or 0), max(1, min(100, int(importance))))
            found["updated_at"] = now
            found["source_node"] = str(source_node or found.get("source_node") or node_name())[:128]
            item = found
        else:
            item = {
                "id": iid,
                "scope": scope,
                "text": text,
                "importance": max(1, min(100, int(importance))),
                "created_at": now,
                "updated_at": now,
                "source_node": str(source_node or node_name())[:128],
            }
            data["items"].append(item)
        data["items"] = sorted(data["items"], key=lambda x: (x["updated_at"], x["importance"]))[-MAX_ITEMS:]
        self.save(data)
        return dict(item)

    @_transaction
    def merge(self, incoming: list[dict]) -> dict:
        data = self.load()
        by_id = {str(x.get("id")): x for x in data["items"] if x.get("id")}
        added = updated = 0
        for row in incoming or []:
            if not isinstance(row, dict):
                continue
            scope = str(row.get("scope") or "").strip().lower()
            text = _clean_text(row.get("text") or "")
            # Node memories never leave their owner; ignore remote node scope.
            if (not text and not (row.get("deleted") and row.get("id"))) or not (scope == "shared" or scope.startswith("persona:")):
                continue
            iid = str(row.get("id") or _item_id(scope, text))
            candidate = {
                "id": iid,
                "scope": scope,
                "text": text,
                "importance": max(1, min(100, int(row.get("importance") or 60))),
                "created_at": float(row.get("created_at") or time.time()),
                "updated_at": float(row.get("updated_at") or row.get("created_at") or time.time()),
                "source_node": str(row.get("source_node") or "peer")[:128],
                **_provenance(row),
            }
            old = by_id.get(iid)
            if old is None:
                by_id[iid] = candidate
                added += 1
            elif (candidate["updated_at"], candidate.get("revision",1), candidate["source_node"], candidate["text"]) > (float(old.get("updated_at") or 0), old.get("revision",1), old["source_node"], old["text"]):
                by_id[iid] = candidate
                updated += 1
        items = sorted(by_id.values(), key=lambda x: (x["updated_at"], x["importance"]))[-MAX_ITEMS:]
        data = {"version": VERSION, "items": items, "atoms": self.load().get("atoms",[])}
        self.save(data)
        return {"ok": True, "added": added, "updated": updated, "count": len(items)}

    def public(self, include_local: bool = True) -> dict:
        items = self.load()["items"]
        if not include_local:
            items = [x for x in items if x.get("scope") == "shared" or str(x.get("scope") or "").startswith("persona:")]
        atoms=self.load().get("atoms",[])
        if not include_local:
            atoms=[x for x in atoms if x.get("scope")=="shared" or str(x.get("scope") or "").startswith("persona:")]
        return {"version": VERSION, "node": node_name(), "items": items, "atoms": atoms}

    @_transaction
    def add_atom(self, scope: str, kind: str, subject: str, relation: str = "", value: str = "", confidence: int = 70, source_node: str | None = None) -> dict:
        scope=str(scope or "shared").strip().lower()
        if not _valid_scope(scope): raise ValueError("scope must be shared, persona:<name>, or node:<name>")
        subject=_clean_text(subject)[:180]; relation=_clean_text(relation)[:80]; value=_clean_text(value)[:360]
        if not (subject or value): raise ValueError("atom subject or value required")
        now=time.time(); data=self.load()
        raw="|".join([str(kind or "fact")[:32],subject,relation,value])
        iid=_item_id(scope,raw)
        found=next((x for x in data.get("atoms",[]) if x.get("id")==iid),None)
        if found:
            found["u"]=int(found.get("u",1))+1; found["c"]=min(100,max(int(found.get("c",70)),int(confidence))+2)
            found["updated_at"]=now; found["source_node"]=str(source_node or found.get("source_node") or node_name())[:128]
            atom=found
        else:
            atom={"id":iid,"scope":scope,"k":str(kind or "fact")[:32],"s":subject,"r":relation,"v":value,
                  "c":max(1,min(100,int(confidence))),"u":1,"updated_at":now,"source_node":str(source_node or node_name())[:128]}
            data.setdefault("atoms",[]).append(atom)
        data["atoms"]=sorted(data.get("atoms",[]),key=lambda x:(x.get("updated_at",0),x.get("c",0),x.get("u",1)))[-MAX_ATOMS:]
        self.save(data); return dict(atom)

    @_transaction
    def merge_atoms(self, incoming: list[dict]) -> dict:
        data=self.load(); by_id={str(x.get("id")):x for x in data.get("atoms",[]) if x.get("id")}; added=updated=0
        for row in incoming or []:
            if not isinstance(row,dict): continue
            scope=str(row.get("scope") or "").strip().lower()
            if not (scope=="shared" or scope.startswith("persona:")): continue
            subject=_clean_text(row.get("s") or row.get("subject") or "")[:180]; value=_clean_text(row.get("v") or row.get("value") or "")[:360]
            if not (subject or value): continue
            relation=_clean_text(row.get("r") or row.get("relation") or "")[:80]; kind=str(row.get("k") or "fact")[:32]
            iid=str(row.get("id") or _item_id(scope,"|".join([kind,subject,relation,value])))
            candidate={"id":iid,"scope":scope,"k":kind,"s":subject,"r":relation,"v":value,
                       "c":max(1,min(100,int(row.get("c",70) or 70))),"u":max(1,int(row.get("u",1) or 1)),
                       "updated_at":float(row.get("updated_at") or row.get("t") or time.time()),"source_node":str(row.get("source_node") or "peer")[:128]}
            old=by_id.get(iid)
            if old is None: by_id[iid]=candidate; added+=1
            elif candidate["updated_at"]>float(old.get("updated_at") or 0): by_id[iid]=candidate; updated+=1
        data["atoms"]=sorted(by_id.values(),key=lambda x:(x.get("updated_at",0),x.get("c",0),x.get("u",1)))[-MAX_ATOMS:]
        self.save(data); return {"ok":True,"added":added,"updated":updated,"count":len(data["atoms"])}

    def relevant_atoms(self, persona: str | None = None, query: str = "", limit: int = 12, include_local: bool = True) -> list[dict]:
        q={t for t in "".join(c.lower() if c.isalnum() else " " for c in str(query or "")).split() if len(t)>2}
        allowed={"shared"}
        if persona: allowed.add("persona:"+str(persona).strip().lower())
        if include_local: allowed.add("node:"+node_name().lower())
        ranked=[]; now=time.time()
        for atom in self.load().get("atoms",[]):
            if str(atom.get("scope") or "").lower() not in allowed: continue
            material=" ".join(str(atom.get(k) or "") for k in ("k","s","r","v"))
            words={t for t in "".join(c.lower() if c.isalnum() else " " for c in material).split() if len(t)>2}
            overlap=len(q & words) if q else 0; age=max(0.0,(now-float(atom.get("updated_at") or now))/86400.0)
            score=overlap*20+int(atom.get("c") or 0)+min(20,int(atom.get("u") or 1)*2)-min(30,age)
            ranked.append((score,atom))
        ranked.sort(key=lambda x:x[0],reverse=True)
        return [dict(x[1]) for x in ranked[:max(1,int(limit))]]

    def relevant(self, persona: str | None = None, query: str = "", limit: int = 8, include_local: bool = True) -> list[dict]:
        q = {t for t in "".join(c.lower() if c.isalnum() else " " for c in str(query or "")).split() if len(t) > 2}
        allowed = {"shared"}
        if persona:
            allowed.add("persona:" + str(persona).strip().lower())
        if include_local:
            allowed.add("node:" + node_name().lower())
        ranked = []
        now = time.time()
        for item in self.load()["items"]:
            if item.get("deleted"): continue
            if str(item.get("scope") or "").lower() not in allowed:
                continue
            words = {t for t in "".join(c.lower() if c.isalnum() else " " for c in item.get("text", "")).split() if len(t) > 2}
            overlap = len(q & words) if q else 0
            importance = int(item.get("importance") or 0)
            age_days = max(0.0, (now - float(item.get("updated_at") or now)) / 86400.0)
            score = overlap * 20 + importance - min(30, age_days)
            ranked.append((score, item))
        ranked.sort(key=lambda x: x[0], reverse=True)
        return [dict(x[1]) for x in ranked[:max(1, int(limit))]]


def context_text(persona: str | None = None, query: str = "", limit: int = 8) -> str:
    rows = FabricMemory().relevant(persona=persona, query=query, limit=limit)
    atoms=FabricMemory().relevant_atoms(persona=persona, query=query, limit=12)
    if not rows and not atoms:
        return ""
    lines = ["Fabric memory (user-owned context; use only when relevant):"]
    for row in rows:
        lines.append(f"- [{row['scope']}] {row['text']}")
    for atom in atoms:
        lines.append(f"- [{atom['scope']}] {atom.get('k')}|{atom.get('s')}|{atom.get('r')}|{atom.get('v')}")
    return "\n".join(lines)
