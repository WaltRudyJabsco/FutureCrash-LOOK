#!/usr/bin/env python3
"""Host observation plane for present-tense typed objects.

Observers report what the operating system exposes *now*.  They never grant
permission and never execute user-requested mutations.  Results are reconciled
into Live State by the host edge.
"""
from __future__ import annotations

import os, re, shutil, subprocess, sys, time
from typing import Any

LOOK_TOKEN_RE=re.compile(r"LOOK-(term_[A-Za-z0-9_-]+)")


def _run(argv:list[str], timeout:float=3.0)->str:
    try:
        p=subprocess.run(argv,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,text=True,timeout=timeout)
        return p.stdout or "" if p.returncode==0 else ""
    except (OSError,subprocess.SubprocessError):
        return ""


def _linux_windows()->tuple[list[dict[str,Any]],str]:
    """Observe X11/XWayland windows when a semantic enumerator is available."""
    wmctrl=shutil.which("wmctrl")
    if not wmctrl or not (os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY")):
        return [],""
    out=_run([wmctrl,"-lpGx"],3.0)
    if not out: return [],""
    rows=[]; now=time.time()
    active_id=""
    xprop=shutil.which("xprop")
    if xprop:
        active=_run([xprop,"-root","_NET_ACTIVE_WINDOW"],2.0)
        m=re.search(r"window id # (0x[0-9a-fA-F]+)",active)
        if m: active_id=m.group(1).lower()
    # wmctrl -lpGx: id desktop pid x y w h class host/title...
    for line in out.splitlines():
        parts=line.split(None,9)
        if len(parts)<9: continue
        wid,desktop,pid,x,y,w,h,wmclass=parts[:8]
        title=parts[9] if len(parts)>9 else parts[8] if len(parts)>8 else ""
        token=LOOK_TOKEN_RE.search(title)
        obj_id=token.group(1) if token else f"win_{wid.lower().replace('0x','')}"
        kind="terminal_window" if token else "desktop_window"
        try: ipid=int(pid)
        except ValueError: ipid=0
        row={
            "id":obj_id,"kind":kind,"platform":"linux","os_window_id":wid,
            "title":title,"app_class":wmclass,"status":"open","observed_at":now,
            "source":"window_inspector","observer":"linux-wmctrl","focused":wid.lower()==active_id,
            "bounds":{"x":int(x),"y":int(y),"width":int(w),"height":int(h)},
        }
        if ipid>1: row["pid"]=ipid
        if token: row["window_token"]=f"LOOK-{obj_id}"
        rows.append(row)
    return rows,"linux-wmctrl"


def _mac_terminal_windows()->tuple[list[dict[str,Any]],str]:
    osa=shutil.which("osascript")
    if not osa: return [],""
    script=(
        'tell application "Terminal"\n'
        'set frontID to ""\n'
        'if (count of windows) > 0 then set frontID to (id of front window as text)\n'
        'set out to "FRONT" & tab & frontID & linefeed\n'
        'repeat with w in windows\n'
        'set out to out & (id of w as text) & tab & (name of w as text) & linefeed\n'
        'end repeat\n'
        'return out\n'
        'end tell'
    )
    out=_run([osa,"-e",script],4.0)
    if not out: return [],"macos-terminal-applescript"
    rows=[]; now=time.time(); front_id=""
    lines=out.splitlines()
    if lines and lines[0].startswith("FRONT\t"):
        front_id=lines[0].split("\t",1)[1].strip(); lines=lines[1:]
    for line in lines:
        if "\t" not in line: continue
        wid,title=line.split("\t",1)
        wid=wid.strip(); title=title.strip()
        if not wid: continue
        rows.append({
            "id":f"term_macos_{wid}","kind":"terminal_window","platform":"darwin",
            "os_window_id":wid,"title":title,"status":"open","observed_at":now,
            "source":"window_inspector","observer":"macos-terminal-applescript","focused":wid==front_id,
        })
    return rows,"macos-terminal-applescript"


def observe_windows()->dict[str,Any]:
    if sys.platform=="darwin": rows,observer=_mac_terminal_windows()
    elif sys.platform.startswith("linux"): rows,observer=_linux_windows()
    else: rows,observer=[],""
    return {
        "domain":"windows","observer":observer,"authoritative":bool(observer),
        "observed_at":time.time(),"objects":rows,
    }


def observe(domains:list[str]|tuple[str,...]|None=None)->dict[str,Any]:
    wanted=set(domains or ("windows",))
    result={"observed_at":time.time(),"domains":{}}
    if "windows" in wanted: result["domains"]["windows"]=observe_windows()
    return result
