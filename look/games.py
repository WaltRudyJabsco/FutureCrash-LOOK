#!/usr/bin/env python3
"""LOOK Games — tiny deterministic terminal games with a shared WarGames shell.

The games deliberately avoid heavyweight engine dependencies.  They are terminal
Easter eggs: correct enough to be genuinely playable, small enough to audit.
"""
from __future__ import annotations

import math
import os
import random
import re
import select
import shutil
import subprocess
import sys
import json
import urllib.request
import shlex
import termios
import time
import tty
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

RESET="\033[0m"
CYAN="\033[38;5;45m"
BRIGHT="\033[1;38;5;51m"
DIM="\033[38;5;31m"
WHITE="\033[1;38;5;255m"
RED="\033[38;5;196m"
YELLOW="\033[38;5;220m"
BG_LIGHT="\033[48;5;238m"
BG_DARK="\033[48;5;234m"
MENU_RETURN=10


def _clear() -> str:
    return "\033[2J\033[H"


@contextmanager
def terminal():
    if not (sys.stdin.isatty() and sys.stdout.isatty()):
        raise RuntimeError("games require an interactive terminal")
    fd=sys.stdin.fileno(); old=termios.tcgetattr(fd)
    try:
        tty.setcbreak(fd)
        sys.stdout.write("\033[?1049h\033[?25l"+_clear()); sys.stdout.flush()
        yield fd
    finally:
        termios.tcsetattr(fd,termios.TCSADRAIN,old)
        sys.stdout.write("\033[?25h\033[?1049l"); sys.stdout.flush()


def read_key(fd:int, timeout:float|None=None):
    if timeout is not None:
        ready,_,_=select.select([fd],[],[],max(0.0,timeout))
        if not ready: return None
    ch=os.read(fd,1)
    if not ch: return None
    if ch==b"\x1b":
        # Drain the rest of an arrow-key escape sequence when present.
        seq=ch
        while True:
            ready,_,_=select.select([fd],[],[],0.001)
            if not ready: break
            seq+=os.read(fd,1)
        return {b"\x1b[A":"up",b"\x1b[B":"down",b"\x1b[C":"right",b"\x1b[D":"left"}.get(seq,"esc")
    if ch in {b"\r",b"\n"}: return "enter"
    try: return ch.decode("utf-8","ignore").lower()
    except Exception: return ""


def read_line(fd:int, prompt:str, *, allow_empty:bool=False) -> str:
    """Tiny cbreak line editor so games keep the alternate-screen shell."""
    buf=[]
    sys.stdout.write(prompt); sys.stdout.write("\033[?25h"); sys.stdout.flush()
    try:
        while True:
            key=read_key(fd)
            if key=="enter":
                if buf or allow_empty:
                    sys.stdout.write("\n"); sys.stdout.flush(); return "".join(buf).strip()
                continue
            if key=="esc": return "q"
            if key in {"\x7f","\b"}:
                if buf:
                    buf.pop(); sys.stdout.write("\b \b"); sys.stdout.flush()
                continue
            if isinstance(key,str) and len(key)==1 and key.isprintable():
                buf.append(key); sys.stdout.write(key); sys.stdout.flush()
    finally:
        sys.stdout.write("\033[?25l"); sys.stdout.flush()


def chrome(title:str, mode:str, turn:str="", status:str="") -> list[str]:
    lines=[_clear()+BRIGHT+"LOOK GAMES // WOPR RECREATION CHANNEL"+RESET,
           CYAN+f"{title.upper()}   ·   {mode.upper()}"+RESET]
    if turn: lines.append(DIM+turn+RESET)
    if status: lines.append(WHITE+status+RESET)
    lines.append("")
    return lines


def footer(mode:str) -> str:
    if mode=="0p": return DIM+"space pause/resume   s stop   r restart   h help   q/esc menu"+RESET
    return DIM+"s stop   r restart   h help   q/esc menu"+RESET


def _wopr_local_fallback(clean:str) -> bool:
    """Use the same proven eSpeak NG + SoX chain on macOS and Linux."""
    speak=shutil.which("espeak-ng")
    play=shutil.which("play")
    if speak:
        try:
            if play:
                command=(f"{shlex.quote(speak)} --stdout -s 135 -p 25 -v en-us {shlex.quote(clean)} | "
                         f"{shlex.quote(play)} -q -t wav - pitch -250 chorus 0.6 0.9 55 0.4 0.25 2 -t")
                subprocess.Popen(["/bin/sh","-c",command],stdin=subprocess.DEVNULL,
                                 stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,start_new_session=True)
            else:
                subprocess.Popen([speak,"-s","135","-p","25","-v","en-us",clean],
                                 stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,start_new_session=True)
            return True
        except OSError:
            pass
    if sys.platform=="darwin" and shutil.which("say"):
        try:
            subprocess.Popen([shutil.which("say"),"-r","145",clean],stdout=subprocess.DEVNULL,
                             stderr=subprocess.DEVNULL,start_new_session=True)
            return True
        except OSError:
            pass
    return False


def wopr_say(text:str) -> bool:
    """Speak through Fabric first; direct local synthesis is the offline fallback."""
    if os.environ.get("LOOK_GAMES_VOICE", "1").casefold() in {"0","off","false","no"}:
        return False
    clean=" ".join(str(text).split())
    if not clean: return False
    try:
        body=json.dumps({"text":clean,"voice_profile":"wopr"}).encode()
        req=urllib.request.Request("http://127.0.0.1:7332/v1/audio/speak",data=body,
                                   headers={"Content-Type":"application/json"},method="POST")
        with urllib.request.urlopen(req,timeout=.45) as resp:
            if 200 <= int(resp.status) < 300:
                return True
    except Exception:
        pass
    return _wopr_local_fallback(clean)


def help_screen(fd:int, title:str, text:Iterable[str]):
    sys.stdout.write(_clear()+BRIGHT+title.upper()+RESET+"\n\n"+"\n".join(text)+"\n\n"+DIM+"press any key"+RESET)
    sys.stdout.flush(); read_key(fd)


def mode_from(value:str|None, default="1p") -> str:
    v=(value or default).casefold().replace("-","")
    aliases={"0":"0p","0p":"0p","demo":"0p","cpu":"0p","1":"1p","1p":"1p","solo":"1p","2":"2p","2p":"2p","local":"2p"}
    if v not in aliases: raise ValueError("mode must be 0p, 1p, or 2p")
    return aliases[v]


def wopr_outcome(kind:str="ordinary") -> None:
    """Sparse end-state commentary; GTNW owns its original dramatic ending."""
    if kind=="draw":
        wopr_say("INTERESTING. A DRAW.")
    elif kind=="checkmate":
        wopr_say("INTERESTING. A FORCED CONCLUSION.")
    else:
        wopr_say("INTERESTING. THE GAME IS COMPLETE.")


# ── Tic-tac-toe ──────────────────────────────────────────────────────────────
_TTT_LINES=((0,1,2),(3,4,5),(6,7,8),(0,3,6),(1,4,7),(2,5,8),(0,4,8),(2,4,6))


def ttt_winner(board:list[str]):
    for a,b,c in _TTT_LINES:
        if board[a] and board[a]==board[b]==board[c]: return board[a]
    return "D" if all(board) else None


def ttt_score(board:list[str], player:str) -> int:
    result=ttt_winner(board)
    if result=="X": return 10
    if result=="O": return -10
    if result=="D": return 0
    scores=[]
    for i,v in enumerate(board):
        if not v:
            board[i]=player; scores.append(ttt_score(board,"O" if player=="X" else "X")); board[i]=""
    return max(scores) if player=="X" else min(scores)


def ttt_ai(board:list[str], player:str) -> int|None:
    scored=[]
    for i,v in enumerate(board):
        if not v:
            board[i]=player; score=ttt_score(board,"O" if player=="X" else "X"); board[i]=""
            scored.append((score,i))
    if not scored: return None
    best=(max(s for s,_ in scored) if player=="X" else min(s for s,_ in scored))
    return random.choice([i for s,i in scored if s==best])


def render_ttt(board, mode, turn, notice=""):
    def c(i): return (BRIGHT+board[i]+RESET) if board[i] else str(i+1)
    rows=[f"       {c(0)} │ {c(1)} │ {c(2)}", "      ───┼───┼───",
          f"       {c(3)} │ {c(4)} │ {c(5)}", "      ───┼───┼───",
          f"       {c(6)} │ {c(7)} │ {c(8)}"]
    sys.stdout.write("\n".join(chrome("Tic-Tac-Toe",mode,f"TURN {turn}",notice)+rows+["",footer(mode)])); sys.stdout.flush()


def play_ttt(mode="1p"):
    with terminal() as fd:
        board=[""]*9; turn="X"; paused=False; notice=""; announced_result=None
        while True:
            result=ttt_winner(board)
            render_ttt(board,mode,turn,notice)
            if result:
                if announced_result != result:
                    wopr_outcome("draw" if result=="D" else "ordinary"); announced_result=result
                notice="DRAW." if result=="D" else f"{result} WINS."
                render_ttt(board,mode,turn,notice+"  r restart · q menu")
                k=read_key(fd)
                if k=="r": board=[""]*9; turn="X"; notice=""; announced_result=None; continue
                if k in {"q","esc"}: return MENU_RETURN
                if k=="s": return 0
                continue
            ai_turn=(mode=="0p") or (mode=="1p" and turn=="O")
            if ai_turn:
                key=read_key(fd,0.35)
                if key in {"q","esc"}: return MENU_RETURN
                if key=="s": return 0
                if key=="r": board=[""]*9; turn="X"; continue
                if key==" ": paused=not paused; notice="PAUSED" if paused else ""
                if key=="h": help_screen(fd,"Tic-Tac-Toe",["Choose 1-9.","0p lets both computers play.","Perfect minimax. No advantage discovered."])
                if paused: continue
                move=ttt_ai(board,turn)
                if move is not None: board[move]=turn; turn="O" if turn=="X" else "X"
                continue
            raw=read_line(fd,"move 1-9 > ")
            if raw=="q": return MENU_RETURN
            if raw=="s": return 0
            if raw=="r": board=[""]*9; turn="X"; continue
            if raw=="h": help_screen(fd,"Tic-Tac-Toe",["Choose 1-9.","X moves first.","s stops; r restarts."]); continue
            if raw.isdigit() and 1<=int(raw)<=9 and not board[int(raw)-1]:
                board[int(raw)-1]=turn; turn="O" if turn=="X" else "X"; notice=""
            else: notice="ILLEGAL MOVE."


# ── Chess ────────────────────────────────────────────────────────────────────
FILES="abcdefgh"
KNIGHT=((1,2),(2,1),(2,-1),(1,-2),(-1,-2),(-2,-1),(-2,1),(-1,2))
KING=((1,1),(1,0),(1,-1),(0,1),(0,-1),(-1,1),(-1,0),(-1,-1))
BISHOP=((1,1),(1,-1),(-1,1),(-1,-1))
ROOK=((1,0),(-1,0),(0,1),(0,-1))
VALUES={"p":100,"n":320,"b":330,"r":500,"q":900,"k":20000}


def sq(file:int, rank:int): return rank*8+file

def xy(i:int): return (i%8,i//8)

def coord(i:int):
    x,y=xy(i); return FILES[x]+str(y+1)

def parse_sq(s:str):
    s=s.strip().lower()
    if len(s)!=2 or s[0] not in FILES or s[1] not in "12345678": return None
    return sq(FILES.index(s[0]),int(s[1])-1)


def chess_initial():
    b=[""]*64
    b[0:8]=list("RNBQKBNR"); b[8:16]=["P"]*8
    b[48:56]=["p"]*8; b[56:64]=list("rnbqkbnr")
    return b


def side(piece:str): return "W" if piece.isupper() else "B"


def pseudo_chess(board, who:str):
    out=[]
    for i,p in enumerate(board):
        if not p or side(p)!=who: continue
        x,y=xy(i); low=p.lower()
        if low=="p":
            dy=1 if who=="W" else -1; start=1 if who=="W" else 6
            ny=y+dy
            if 0<=ny<8:
                j=sq(x,ny)
                if not board[j]:
                    out.append((i,j,"q" if ny in {0,7} else ""))
                    if y==start:
                        j2=sq(x,y+2*dy)
                        if not board[j2]: out.append((i,j2,""))
                for dx in (-1,1):
                    nx=x+dx
                    if 0<=nx<8:
                        j=sq(nx,ny)
                        if board[j] and side(board[j])!=who: out.append((i,j,"q" if ny in {0,7} else ""))
        elif low=="n":
            for dx,dy in KNIGHT:
                nx,ny=x+dx,y+dy
                if 0<=nx<8 and 0<=ny<8:
                    j=sq(nx,ny)
                    if not board[j] or side(board[j])!=who: out.append((i,j,""))
        elif low in {"b","r","q"}:
            dirs=(BISHOP if low=="b" else ROOK if low=="r" else BISHOP+ROOK)
            for dx,dy in dirs:
                nx,ny=x+dx,y+dy
                while 0<=nx<8 and 0<=ny<8:
                    j=sq(nx,ny)
                    if not board[j]: out.append((i,j,""))
                    else:
                        if side(board[j])!=who: out.append((i,j,""))
                        break
                    nx+=dx; ny+=dy
        elif low=="k":
            for dx,dy in KING:
                nx,ny=x+dx,y+dy
                if 0<=nx<8 and 0<=ny<8:
                    j=sq(nx,ny)
                    if not board[j] or side(board[j])!=who: out.append((i,j,""))
    return out


def chess_apply(board, move):
    a,b,promo=move; nb=board.copy(); piece=nb[a]; nb[a]=""; nb[b]=piece
    if promo and piece.lower()=="p": nb[b]=promo.upper() if piece.isupper() else promo.lower()
    return nb


def chess_attacked(board, target:int, by:str):
    # Attack maps differ from move maps for pawns: a pawn attacks diagonally,
    # never the empty square directly in front of it. Keep this independent
    # from legal-move filtering so king safety cannot recurse.
    tx,ty=xy(target)
    for i,p in enumerate(board):
        if not p or side(p)!=by: continue
        x,y=xy(i); low=p.lower()
        if low=="p":
            dy=1 if by=="W" else -1
            if ty==y+dy and abs(tx-x)==1: return True
        elif low=="n":
            if (tx-x,ty-y) in KNIGHT: return True
        elif low=="k":
            if (tx-x,ty-y) in KING: return True
        elif low in {"b","r","q"}:
            dirs=(BISHOP if low=="b" else ROOK if low=="r" else BISHOP+ROOK)
            for dx,dy in dirs:
                nx,ny=x+dx,y+dy
                while 0<=nx<8 and 0<=ny<8:
                    j=sq(nx,ny)
                    if j==target: return True
                    if board[j]: break
                    nx+=dx; ny+=dy
    return False


def chess_in_check(board, who:str):
    king="K" if who=="W" else "k"
    try: k=board.index(king)
    except ValueError: return True
    return chess_attacked(board,k,"B" if who=="W" else "W")


def chess_moves(board, who:str):
    return [m for m in pseudo_chess(board,who) if not chess_in_check(chess_apply(board,m),who)]


def chess_eval(board):
    score=0
    for p in board:
        if p: score+=(VALUES[p.lower()] if p.isupper() else -VALUES[p.lower()])
    return score


def chess_ai(board, who:str, depth:int=2):
    moves=chess_moves(board,who)
    if not moves: return None
    def search(pos, turn, d, alpha=-10**9, beta=10**9):
        moves2=chess_moves(pos,turn)
        if d<=0 or not moves2: return chess_eval(pos)
        if turn=="W":
            value=-10**9
            for m in moves2:
                value=max(value,search(chess_apply(pos,m),"B",d-1,alpha,beta)); alpha=max(alpha,value)
                if beta<=alpha: break
            return value
        value=10**9
        for m in moves2:
            value=min(value,search(chess_apply(pos,m),"W",d-1,alpha,beta)); beta=min(beta,value)
            if beta<=alpha: break
        return value
    scored=[]
    for m in moves:
        v=search(chess_apply(board,m),"B" if who=="W" else "W",depth-1)
        scored.append((v,m))
    best=(max(v for v,_ in scored) if who=="W" else min(v for v,_ in scored))
    choices=[m for v,m in scored if v==best]
    return random.choice(choices)


def render_chess(board, mode, who, status=""):
    glyph={"K":"K","Q":"Q","R":"R","B":"B","N":"N","P":"P","k":"k","q":"q","r":"r","b":"b","n":"n","p":"p"}
    lines=["      a  b  c  d  e  f  g  h"]
    for y in range(7,-1,-1):
        row=[]
        for x in range(8):
            p=board[sq(x,y)] or " "
            bg=BG_LIGHT if (x+y)%2==0 else BG_DARK
            if p.strip():
                fg=BRIGHT if p.isupper() else CYAN
                cell=bg+fg+" "+glyph.get(p,p)+" "+RESET
            else:
                mark="·" if (x+y)%2==0 else " "
                cell=bg+DIM+" "+mark+" "+RESET
            row.append(cell)
        lines.append(f" {y+1}   "+"".join(row)+f"  {y+1}")
    lines += ["      a  b  c  d  e  f  g  h", "", footer(mode)]
    sys.stdout.write("\n".join(chrome("Chess",mode,"WHITE" if who=="W" else "BLACK",status)+lines)); sys.stdout.flush()


def play_chess(mode="1p"):
    with terminal() as fd:
        board=chess_initial(); who="W"; paused=False; status=""; announced_end=False
        while True:
            moves=chess_moves(board,who)
            if not moves:
                mate=chess_in_check(board,who)
                if not announced_end:
                    wopr_outcome("checkmate" if mate else "draw"); announced_end=True
                status=("CHECKMATE. "+("BLACK WINS." if who=="W" else "WHITE WINS.")) if mate else "STALEMATE."
                render_chess(board,mode,who,status+"  r restart · q menu")
                k=read_key(fd)
                if k=="r": board=chess_initial(); who="W"; status=""; announced_end=False; continue
                if k in {"q","esc"}: return MENU_RETURN
                if k=="s": return 0
                continue
            render_chess(board,mode,who,status)
            ai_turn=(mode=="0p") or (mode=="1p" and who=="B")
            if ai_turn:
                key=read_key(fd,0.30)
                if key in {"q","esc"}: return MENU_RETURN
                if key=="s": return 0
                if key=="r": board=chess_initial(); who="W"; continue
                if key==" ": paused=not paused; status="PAUSED" if paused else ""
                if key=="h": help_screen(fd,"Chess",["Enter moves as e2e4 or e7e8q.","Compact engine: normal moves, captures, promotion, check/checkmate.","Castling and en passant are intentionally omitted."])
                if paused: continue
                m=chess_ai(board,who,2)
                if m: status=f"{coord(m[0])} → {coord(m[1])}"; board=chess_apply(board,m); who="B" if who=="W" else "W"
                continue
            raw=read_line(fd,"move (e2e4) > ")
            if raw=="q": return MENU_RETURN
            if raw=="s": return 0
            if raw=="r": board=chess_initial(); who="W"; status=""; continue
            if raw=="h": help_screen(fd,"Chess",["Enter moves as e2e4 or e7e8q.","White moves first.","Castling/en passant omitted to keep the Easter egg tiny."]); continue
            compact=re.sub(r"[^a-h1-8qrbn]","",raw.lower())
            if len(compact)>=4:
                a=parse_sq(compact[:2]); b=parse_sq(compact[2:4]); promo=compact[4] if len(compact)>4 else ""
                matches=[m for m in moves if m[0]==a and m[1]==b and (not m[2] or not promo or m[2]==promo)]
                if matches:
                    m=matches[0]
                    if promo and m[2]: m=(m[0],m[1],promo)
                    board=chess_apply(board,m); status=f"{coord(m[0])} → {coord(m[1])}"; who="B" if who=="W" else "W"; continue
            status="ILLEGAL MOVE."


# ── Checkers ─────────────────────────────────────────────────────────────────
def checkers_initial():
    b=[""]*64
    for y in range(3):
        for x in range(8):
            if (x+y)%2==1: b[sq(x,y)]="w"
    for y in range(5,8):
        for x in range(8):
            if (x+y)%2==1: b[sq(x,y)]="b"
    return b


def checker_side(p): return "W" if p.lower()=="w" else "B"

def _checker_dirs(p):
    return ((-1,1),(1,1),(-1,-1),(1,-1)) if p.isupper() else (((-1,1),(1,1)) if p=="w" else ((-1,-1),(1,-1)))


def _checker_captures(board, start, p, path=None):
    path=path or [start]; x,y=xy(start); found=[]
    for dx,dy in _checker_dirs(p):
        mx,my=x+dx,y+dy; nx,ny=x+2*dx,y+2*dy
        if 0<=nx<8 and 0<=ny<8 and 0<=mx<8 and 0<=my<8:
            mid=sq(mx,my); dest=sq(nx,ny)
            if board[mid] and checker_side(board[mid])!=checker_side(p) and not board[dest]:
                nb=board.copy(); nb[start]=""; nb[mid]=""; np=p
                if p=="w" and ny==7: np="W"
                if p=="b" and ny==0: np="B"
                nb[dest]=np
                tails=_checker_captures(nb,dest,np,path+[dest])
                found.extend(tails or [(path+[dest],nb)])
    return found


def checkers_moves(board, who):
    captures=[]; normals=[]
    for i,p in enumerate(board):
        if not p or checker_side(p)!=who: continue
        captures.extend(_checker_captures(board,i,p))
        x,y=xy(i)
        for dx,dy in _checker_dirs(p):
            nx,ny=x+dx,y+dy
            if 0<=nx<8 and 0<=ny<8:
                j=sq(nx,ny)
                if not board[j]:
                    nb=board.copy(); nb[i]=""; np=p
                    if p=="w" and ny==7: np="W"
                    if p=="b" and ny==0: np="B"
                    nb[j]=np; normals.append(([i,j],nb))
    return captures or normals


def checkers_eval(board):
    s=0
    for i,p in enumerate(board):
        if p:
            val=5 if p.isupper() else 3
            _,y=xy(i); val += (y*.08 if p.lower()=="w" else (7-y)*.08)
            s += val if p.lower()=="w" else -val
    return s


def checkers_ai(board, who, depth=3):
    moves=checkers_moves(board,who)
    if not moves: return None
    def search(pos, turn, d, alpha=-9999,beta=9999):
        mm=checkers_moves(pos,turn)
        if d<=0 or not mm: return checkers_eval(pos)
        if turn=="W":
            v=-9999
            for _,np in mm:
                v=max(v,search(np,"B",d-1,alpha,beta)); alpha=max(alpha,v)
                if beta<=alpha: break
            return v
        v=9999
        for _,np in mm:
            v=min(v,search(np,"W",d-1,alpha,beta)); beta=min(beta,v)
            if beta<=alpha: break
        return v
    scored=[(search(np,"B" if who=="W" else "W",depth-1),path,np) for path,np in moves]
    best=max(s for s,_,_ in scored) if who=="W" else min(s for s,_,_ in scored)
    return random.choice([(p,np) for s,p,np in scored if s==best])


def render_checkers(board, mode, who, status=""):
    lines=["      a  b  c  d  e  f  g  h"]
    for y in range(7,-1,-1):
        row=[]
        for x in range(8):
            p=board[sq(x,y)]
            bg=BG_LIGHT if (x+y)%2==0 else BG_DARK
            if p:
                if p.lower()=="w": piece="◎" if p.isupper() else "○"
                else: piece="◉" if p.isupper() else "●"
                fg=BRIGHT if p.lower()=="w" else RED
                cell=bg+fg+" "+piece+" "+RESET
            else:
                mark="·" if (x+y)%2==0 else " "
                cell=bg+DIM+" "+mark+" "+RESET
            row.append(cell)
        lines.append(f" {y+1}   "+"".join(row)+f"  {y+1}")
    lines += ["      a  b  c  d  e  f  g  h", "", footer(mode)]
    sys.stdout.write("\n".join(chrome("Checkers",mode,"WHITE" if who=="W" else "BLACK",status)+lines)); sys.stdout.flush()


def play_checkers(mode="1p"):
    with terminal() as fd:
        board=checkers_initial(); who="W"; paused=False; status=""; announced_end=False
        while True:
            moves=checkers_moves(board,who)
            if not moves:
                if not announced_end: wopr_outcome(); announced_end=True
                status=("BLACK WINS." if who=="W" else "WHITE WINS.")+"  r restart · q menu"
                render_checkers(board,mode,who,status); k=read_key(fd)
                if k=="r": board=checkers_initial(); who="W"; status=""; announced_end=False; continue
                if k in {"q","esc"}: return MENU_RETURN
                if k=="s": return 0
                continue
            render_checkers(board,mode,who,status)
            ai_turn=(mode=="0p") or (mode=="1p" and who=="B")
            if ai_turn:
                key=read_key(fd,0.28)
                if key in {"q","esc"}: return MENU_RETURN
                if key=="s": return 0
                if key=="r": board=checkers_initial(); who="W"; continue
                if key==" ": paused=not paused; status="PAUSED" if paused else ""
                if key=="h": help_screen(fd,"Checkers",["Enter paths like b2a3 or c3e5g7.","Captures are mandatory; multiple jumps stay in one move.","◎/◉ are kings."])
                if paused: continue
                pick=checkers_ai(board,who,3)
                if pick:
                    path,board=pick; status=" → ".join(coord(i) for i in path); who="B" if who=="W" else "W"
                continue
            raw=read_line(fd,"move (b2a3) > ")
            if raw=="q": return MENU_RETURN
            if raw=="s": return 0
            if raw=="r": board=checkers_initial(); who="W"; status=""; continue
            if raw=="h": help_screen(fd,"Checkers",["Enter b2a3 or a capture chain c3e5g7.","Captures are mandatory.","s stops; r restarts."]); continue
            coords=re.findall(r"[a-h][1-8]",raw.lower()); path=[parse_sq(c) for c in coords]
            hit=next(((p,np) for p,np in moves if p==path),None)
            if hit:
                p,board=hit; status=" → ".join(coord(i) for i in p); who="B" if who=="W" else "W"
            else: status="ILLEGAL MOVE."


# ── Backgammon ───────────────────────────────────────────────────────────────
@dataclass
class Backgammon:
    points:list[int]
    bar_w:int=0
    bar_b:int=0
    off_w:int=0
    off_b:int=0


def backgammon_initial():
    p=[0]*25  # points 1..24
    p[24]=2; p[13]=5; p[8]=3; p[6]=5
    p[1]=-2; p[12]=-5; p[17]=-3; p[19]=-5
    return Backgammon(p)


def bg_can_land(g:Backgammon, who, dest):
    if dest<1 or dest>24: return True
    v=g.points[dest]
    return not (v<=-2 if who=="W" else v>=2)


def bg_home(g,who):
    if who=="W": return g.bar_w==0 and all(g.points[i]<=0 for i in range(7,25))
    return g.bar_b==0 and all(g.points[i]>=0 for i in range(1,19))


def bg_legal_sources(g:Backgammon, who, die):
    if who=="W" and g.bar_w:
        dest=25-die; return [0] if bg_can_land(g,who,dest) else []
    if who=="B" and g.bar_b:
        dest=die; return [25] if bg_can_land(g,who,dest) else []
    sources=[]
    for src in range(1,25):
        if (g.points[src]>0) != (who=="W") or g.points[src]==0: continue
        dest=src-die if who=="W" else src+die
        if 1<=dest<=24:
            if bg_can_land(g,who,dest): sources.append(src)
        elif bg_home(g,who):
            if who=="W" and dest<=0:
                exact=src==die; higher=any(g.points[i]>0 for i in range(src+1,7))
                if exact or not higher: sources.append(src)
            elif who=="B" and dest>=25:
                exact=(25-src)==die; lower=any(g.points[i]<0 for i in range(19,src))
                if exact or not lower: sources.append(src)
    return sources


def bg_move(g:Backgammon, who, src, die):
    n=Backgammon(g.points.copy(),g.bar_w,g.bar_b,g.off_w,g.off_b)
    if who=="W":
        if src==0: n.bar_w-=1; dest=25-die
        else: n.points[src]-=1; dest=src-die
        if dest<1: n.off_w+=1; return n
        if n.points[dest]==-1: n.points[dest]=0; n.bar_b+=1
        n.points[dest]+=1
    else:
        if src==25: n.bar_b-=1; dest=die
        else: n.points[src]+=1; dest=src+die
        if dest>24: n.off_b+=1; return n
        if n.points[dest]==1: n.points[dest]=0; n.bar_w+=1
        n.points[dest]-=1
    return n


def bg_eval(g):
    # Positive favors white: borne-off checkers and lower pip count matter most.
    pipw=sum(i*max(0,g.points[i]) for i in range(1,25))+25*g.bar_w
    pipb=sum((25-i)*max(0,-g.points[i]) for i in range(1,25))+25*g.bar_b
    return (g.off_w-g.off_b)*100 + (pipb-pipw)


def bg_ai_source(g,who,die):
    sources=bg_legal_sources(g,who,die)
    if not sources: return None
    scored=[(bg_eval(bg_move(g,who,s,die)),s) for s in sources]
    best=max(v for v,_ in scored) if who=="W" else min(v for v,_ in scored)
    return random.choice([s for v,s in scored if v==best])


def render_bg(g,mode,who,dice,status=""):
    # A real board silhouette: point numbers, two homes, center bar, and round checkers.
    top=list(range(13,19))+list(range(19,25))
    bottom=list(range(12,6,-1))+list(range(6,0,-1))
    def piece_for(point:int):
        v=g.points[point]
        if v>0: return BRIGHT+"○"+RESET, v
        if v<0: return CYAN+"●"+RESET, -v
        return " ", 0
    def stack_row(points, level:int, top_half:bool):
        cells=[]
        for idx,point in enumerate(points):
            piece,count=piece_for(point)
            if count>5 and level==4:
                token=YELLOW+str(count)+RESET
            elif count>level:
                token=piece
            else:
                token=(DIM+("▽" if top_half else "△")+RESET) if level==4 else " "
            cells.append(" "+token+" ")
        return "".join(cells[:6])+"│   │"+"".join(cells[6:])
    lines=[
        "     "+" ".join(f"{p:>2}" for p in top[:6])+" │BAR│ "+" ".join(f"{p:>2}" for p in top[6:]),
        "   ┌──────────────────┬───┬──────────────────┐",
    ]
    for level in range(5): lines.append("   │"+stack_row(top,level,True)+"│")
    lines.append(f"   │                  │ {g.bar_w:1}/{g.bar_b:1} │                  │")
    for level in range(4,-1,-1): lines.append("   │"+stack_row(bottom,level,False)+"│")
    lines += [
        "   └──────────────────┴───┴──────────────────┘",
        "     "+" ".join(f"{p:>2}" for p in bottom[:6])+" │BAR│ "+" ".join(f"{p:>2}" for p in bottom[6:]),
        f"   OFF  WHITE:{g.off_w:>2}  BLACK:{g.off_b:>2}       DICE  {' '.join('⚄' if d==5 else '⚅' if d==6 else str(d) for d in dice) if dice else '—'}",
        "",footer(mode)
    ]
    sys.stdout.write("\n".join(chrome("Backgammon",mode,"WHITE" if who=="W" else "BLACK",status)+lines)); sys.stdout.flush()


def play_backgammon(mode="1p"):
    with terminal() as fd:
        g=backgammon_initial(); who="W"; paused=False; status=""; dice=[]; announced_end=False
        while True:
            if g.off_w>=15 or g.off_b>=15:
                if not announced_end: wopr_outcome(); announced_end=True
                status=("WHITE WINS." if g.off_w>=15 else "BLACK WINS.")+"  r restart · q menu"
                render_bg(g,mode,who,[],status); k=read_key(fd)
                if k=="r": g=backgammon_initial(); who="W"; announced_end=False; continue
                if k in {"q","esc"}: return MENU_RETURN
                if k=="s": return 0
                continue
            if not dice:
                a,b=random.randint(1,6),random.randint(1,6); dice=[a]*4 if a==b else [a,b]
            render_bg(g,mode,who,dice,status)
            ai_turn=(mode=="0p") or (mode=="1p" and who=="B")
            die=dice[0]
            sources=bg_legal_sources(g,who,die)
            if not sources:
                status=f"NO MOVE FOR {die}."; dice.pop(0)
                if not dice: who="B" if who=="W" else "W"
                continue
            if ai_turn:
                key=read_key(fd,0.25)
                if key in {"q","esc"}: return MENU_RETURN
                if key=="s": return 0
                if key=="r": g=backgammon_initial(); who="W"; dice=[]; continue
                if key==" ": paused=not paused; status="PAUSED" if paused else ""
                if key=="h": help_screen(fd,"Backgammon",["No doubling cube; ordinary hits, bar entry, doubles and bearing off.","On your turn enter the source point for each die.","0 denotes the bar only when shown as forced."])
                if paused: continue
                src=bg_ai_source(g,who,die)
                if src is not None:
                    before=src; g=bg_move(g,who,src,die); status=f"{('BAR' if before in {0,25} else before)} / {die}"
                dice.pop(0)
                if not dice: who="B" if who=="W" else "W"
                continue
            if (who=="W" and g.bar_w) or (who=="B" and g.bar_b):
                src=0 if who=="W" else 25
                raw="bar"
            else:
                raw=read_line(fd,f"die {die} · source point > ")
                if raw=="q": return MENU_RETURN
                if raw=="s": return 0
                if raw=="r": g=backgammon_initial(); who="W"; dice=[]; continue
                if raw=="h": help_screen(fd,"Backgammon",["Enter the source point for the shown die.","Bar entries are automatic when required.","No doubling cube; standard hitting/bearing off."]); continue
                try: src=int(raw)
                except ValueError: status="ENTER A POINT 1-24."; continue
            if src not in sources: status="ILLEGAL MOVE."; continue
            g=bg_move(g,who,src,die); status=f"{raw.upper()} / {die}"; dice.pop(0)
            if not dice: who="B" if who=="W" else "W"


# ── WOPR doorway ───────────────────────────────────────────────────────────────
_GAMES_STATE=Path.home()/".local/share/look/games.json"
_GAME_ITEMS=[
    ("1","TIC-TAC-TOE","ttt"),
    ("2","CHECKERS","checkers"),
    ("3","CHESS","chess"),
    ("4","BACKGAMMON","backgammon"),
    ("5","GLOBAL THERMONUCLEAR WAR","gtnw"),
]


def _provisioned() -> bool:
    try:
        import json
        row=json.loads(_GAMES_STATE.read_text(encoding="utf-8"))
        return bool(row.get("joshua"))
    except Exception:
        return False


def _mark_provisioned() -> None:
    import json
    _GAMES_STATE.parent.mkdir(parents=True,exist_ok=True)
    _GAMES_STATE.write_text(json.dumps({"joshua":True},indent=2)+"\n",encoding="utf-8")


def provision_login(fd:int) -> bool:
    """Theatrical gate shown every visit. JOSHUA is a reference, never security."""
    if os.environ.get("LOOK_GAMES_SKIP_LOGON") == "1":
        return True
    while True:
        sys.stdout.write(_clear()+BRIGHT+"WOPR ACCESS TERMINAL"+RESET+"\n\n")
        sys.stdout.write(DIM+"LOGON: "+RESET); sys.stdout.flush()
        value=read_line(fd,"",allow_empty=True).strip().upper()
        if value in {"Q","QUIT"}: return False
        if value=="JOSHUA":
            sys.stdout.write("\n"+CYAN+"GREETINGS PROFESSOR FALKEN."+RESET+"\n")
            sys.stdout.flush(); wopr_say("GREETINGS PROFESSOR FALKEN. SHALL WE PLAY A GAME?"); time.sleep(.65)
            return True
        sys.stdout.write("\n"+DIM+"IDENTIFICATION NOT RECOGNIZED BY SYSTEM"+RESET+"\n")
        sys.stdout.flush(); time.sleep(.8)


def launcher(fd:int, preselected:str=""):
    """Show the WOPR list. A named command arrives preselected but can be changed."""
    selected=preselected if any(g==preselected for _,_,g in _GAME_ITEMS) else ""
    while True:
        lines=chrome("Available Simulations","SELECT")
        for key,name,game in _GAME_ITEMS:
            cursor=">" if game==selected else " "
            lines.append(f" {cursor} {key}   {name}")
        if selected:
            lines += ["",DIM+"enter accept   1-5 choose another   q/esc exit"+RESET]
        else:
            lines += ["",DIM+"choose 1-5   q/esc exit"+RESET]
        sys.stdout.write("\n".join(lines)); sys.stdout.flush()
        k=read_key(fd)
        if k in {"q","esc","s"}: return None
        if k=="enter" and selected: return selected
        for key,_,name in _GAME_ITEMS:
            if k==key:
                selected=name
                break
        else:
            continue
        if not preselected:
            return selected


def choose_mode(fd:int, game:str, default="1p") -> str|None:
    if game=="gtnw": return "0p"
    labels={"0p":"COMPUTER / COMPUTER","1p":"HUMAN / COMPUTER","2p":"HUMAN / HUMAN"}
    while True:
        lines=chrome(next((n for _,n,g in _GAME_ITEMS if g==game),game),"PLAYERS")
        lines += ["  0   COMPUTER / COMPUTER","  1   HUMAN / COMPUTER","  2   HUMAN / HUMAN","",DIM+"choose 0-2   q/esc exit"+RESET]
        sys.stdout.write("\n".join(lines)); sys.stdout.flush()
        k=read_key(fd)
        if k in {"q","esc","s"}: return None
        if k in {"0","1","2"}: return {"0":"0p","1":"1p","2":"2p"}[k]


def _dispatch(game:str, mode:str, gtnw_runner=None) -> int:
    if game=="ttt": return play_ttt(mode)
    if game=="checkers": return play_checkers(mode)
    if game=="chess": return play_chess(mode)
    if game=="backgammon": return play_backgammon(mode)
    if game=="gtnw":
        if mode!="0p":
            print("LOOK games · Global Thermonuclear War is a 0p simulation."); return 2
        return gtnw_runner() if gtnw_runner else 0
    return 2


def run(args:list[str], *, gtnw_runner=None) -> int:
    args=list(args or [])
    aliases={"tic-tac-toe":"ttt","tic":"ttt","draughts":"checkers","bg":"backgammon","war":"gtnw","thermonuclear":"gtnw"}

    # The bare command now performs the full theatrical security gag before
    # denying the existence of the games it plainly knows about.
    if not args:
        if not (sys.stdin.isatty() and sys.stdout.isatty()):
            print("No games installed.")
            return 0
        try:
            with terminal() as fd:
                if not provision_login(fd): return 0
                sys.stdout.write(_clear()+BRIGHT+"WOPR ACCESS TERMINAL"+RESET+"\n\n"+DIM+"NO GAMES INSTALLED."+RESET+"\n")
                sys.stdout.flush(); time.sleep(.9)
        except RuntimeError as exc:
            print(f"LOOK games · {exc}"); return 1
        print("No games installed.")
        return 0

    game=aliases.get(args[0].casefold(),args[0].casefold())
    if game in {"help","list","ls"}:
        print("No games installed."); return 0
    valid={g for _,_,g in _GAME_ITEMS}
    if game not in valid:
        print(f"LOOK games · unknown simulation: {game}"); return 2

    explicit_mode=args[1] if len(args)>1 else None
    try:
        # Even direct power-user launches pass through LOGON. The gag is the
        # entrance ritual, not a remembered authentication credential.
        if explicit_mode is not None:
            mode=mode_from(explicit_mode,"0p" if game=="gtnw" else "1p")
            if sys.stdin.isatty() and sys.stdout.isatty():
                with terminal() as fd:
                    if not provision_login(fd): return 0
        else:
            with terminal() as fd:
                if not provision_login(fd): return 0
                chosen=launcher(fd,game)
                if not chosen: return 0
                game=chosen
                mode=choose_mode(fd,game,"0p" if game=="gtnw" else "1p")
                if not mode: return 0
    except ValueError as exc:
        print(f"LOOK games · {exc}"); return 2
    except RuntimeError as exc:
        print(f"LOOK games · {exc}"); return 1

    title=next((name for _,name,g in _GAME_ITEMS if g==game),game)
    if game!="gtnw": wopr_say(title)

    while True:
        try:
            result=_dispatch(game,mode,gtnw_runner)
        except RuntimeError as exc:
            print(f"LOOK games · {exc}"); return 1
        if game=="gtnw" or result!=MENU_RETURN:
            return result
        # q/esc from a board game returns here; s remains a true stop.
        try:
            with terminal() as fd:
                chosen=launcher(fd,"")
                if not chosen: return 0
                game=chosen
                mode=choose_mode(fd,game,"0p" if game=="gtnw" else "1p")
                if not mode: return 0
        except RuntimeError as exc:
            print(f"LOOK games · {exc}"); return 1
        title=next((name for _,name,g in _GAME_ITEMS if g==game),game)
        if game!="gtnw": wopr_say(title)

