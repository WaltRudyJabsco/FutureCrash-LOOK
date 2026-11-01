"""A small, offline ASCIIMATION player, discovered with lk force."""
from __future__ import annotations

import argparse
import bisect
import curses
from dataclasses import dataclass
import gzip
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile
import termios
import time
import urllib.request

AUTHOR = 'Simon Jansen'
ORIGINAL = 'https://www.asciimation.co.nz/'
REVISION = '38a49ac6d4c9969168bf060fef33c67234d65e2f'
SOURCE = f'https://raw.githubusercontent.com/jimmckeeth/blinkenlights/{REVISION}/starwars.txt'
SHA256 = '1effa0aecde35e6949994712c74812f0ac8f3795e32c96b3425cfb7bafd58e76'
MAX_BYTES = 4 * 1024 * 1024
FRAME_WIDTH = 67
FRAME_HEIGHT = 13
TICKS_PER_SECOND = 15
SEEK_SECONDS = 10
INPUT_POLL_MS = 50
MIN_WIDTH = FRAME_WIDTH + 2
MIN_HEIGHT = FRAME_HEIGHT + 5


@dataclass(frozen=True)
class Frame:
    ticks: int
    lines: tuple[str, ...]


def cache_path():
    return Path.home()/'.cache/look/force/starwars.txt.gz'


def parse(raw):
    if len(raw)>MAX_BYTES:raise ValueError('Animation exceeds the local size limit')
    lines=raw.decode('ascii').splitlines()
    stride=FRAME_HEIGHT+1
    if not lines or len(lines)%stride:raise ValueError('Incomplete animation frame')
    frames=[]
    for offset in range(0,len(lines),stride):
        timing=lines[offset]
        if not timing.isdecimal() or not 1<=int(timing)<=TICKS_PER_SECOND*600:
            raise ValueError('Invalid frame timing')
        picture=tuple(lines[offset+1:offset+stride])
        # Assets are text, never terminal commands, even if supplied from a cache.
        if any(len(line)>FRAME_WIDTH or any(not 32<=ord(char)<=126 for char in line) for line in picture):
            raise ValueError('Invalid character or width in animation')
        frames.append(Frame(int(timing),picture))
    return frames


def validate(raw):
    if hashlib.sha256(raw).hexdigest()!=SHA256:raise ValueError('Animation checksum mismatch; use lk force --fetch to replace the cache')
    return parse(raw)


def read_cache(path):
    if path.stat().st_size>MAX_BYTES:raise ValueError('Animation cache is too large')
    with gzip.open(path,'rb') as source:raw=source.read(MAX_BYTES+1)
    return raw,validate(raw)


def ensure_cache(path=None,refresh=False):
    path=Path(path) if path is not None else cache_path()
    if path.exists() and not refresh:return read_cache(path)
    request=urllib.request.Request(SOURCE,headers={'User-Agent':'FutureCrash-LOOK ASCIIMATION cache'})
    with urllib.request.urlopen(request,timeout=30) as response:raw=response.read(MAX_BYTES+1)
    frames=validate(raw)
    compressed=gzip.compress(raw,mtime=0)
    path.parent.mkdir(parents=True,exist_ok=True)
    fd,name=tempfile.mkstemp(prefix='.force-',dir=path.parent)
    try:
        with os.fdopen(fd,'wb') as output:output.write(compressed);output.flush();os.fsync(output.fileno())
        os.replace(name,path)
    finally:
        if os.path.exists(name):os.unlink(name)
    return raw,frames


def timeline(frames):
    starts=[0]
    for frame in frames:starts.append(starts[-1]+frame.ticks)
    return starts


def frame_at(starts,seconds):
    return max(0,min(len(starts)-2,bisect.bisect_right(starts,seconds*TICKS_PER_SECOND)-1))


def clock_text(seconds):
    seconds=max(0,int(seconds));return f'{seconds//60:02d}:{seconds%60:02d}'


def player(frames,window,now=time.monotonic):
    starts=timeline(frames);duration=starts[-1]/TICKS_PER_SECOND
    curses.raw();window.keypad(True);window.timeout(INPUT_POLL_MS)
    try:curses.curs_set(0)
    except curses.error:pass
    ink,blue,gray=curses.A_NORMAL,curses.A_BOLD,curses.A_DIM
    try:
        if curses.has_colors():
            curses.start_color()
            palette=[(253,234),(75,234),(246,234)] if curses.COLORS>=256 else [(curses.COLOR_WHITE,curses.COLOR_BLACK),(curses.COLOR_BLUE,curses.COLOR_BLACK),(curses.COLOR_WHITE,curses.COLOR_BLACK)]
            for index,(fg,bg) in enumerate(palette,1):curses.init_pair(index,fg,bg)
            ink,blue,gray=curses.color_pair(1),curses.color_pair(2)|curses.A_BOLD,curses.color_pair(3)
            window.bkgd(' ',ink)
    except curses.error:pass
    def write(row,column,text,style):
        try:window.addnstr(row,column,text,max(0,window.getmaxyx()[1]-column-1),style)
        except curses.error:pass
    position=0.0;paused=False;previous=now();last_view=None
    while True:
        current=now();height,width=window.getmaxyx();fits=height>=MIN_HEIGHT and width>=MIN_WIDTH
        if not paused and fits:position=min(duration,position+max(0,current-previous))
        previous=current
        if position>=duration:paused=True
        index=frame_at(starts,position);view=(index,paused,height,width,int(position))
        if view!=last_view:
            window.erase()
            if not fits:
                write(0,0,f'Use at least {MIN_WIDTH} columns × {MIN_HEIGHT} rows. q quits.',gray)
            else:
                left=(width-FRAME_WIDTH)//2;top=max(0,(height-FRAME_HEIGHT-3)//2)
                for row,line in enumerate(frames[index].lines):write(top+row,left,line.ljust(FRAME_WIDTH),ink)
                state='END' if position>=duration else 'PAUSED' if paused else 'PLAYING'
                write(height-3,left,f'{state} · {clock_text(position)} / {clock_text(duration)} · {AUTHOR}',gray)
                column=left
                for key,label in [('Space','pause'),('←/→','10s'),('Home','restart'),('q','quit')]:
                    write(height-1,column,key,blue);column+=len(key)
                    write(height-1,column,' '+label+'  ',gray);column+=len(label)+3
            window.refresh();last_view=view
        try:key=window.get_wch()
        except curses.error:continue
        if key in ('q','Q','\x1b','\x03'):return
        if key==' ':paused=not paused
        elif key in (curses.KEY_LEFT,'h'):position=max(0,position-SEEK_SECONDS)
        elif key in (curses.KEY_RIGHT,'l'):position=min(duration,position+SEEK_SECONDS)
        elif key in (curses.KEY_HOME,'r','R'):position=0;paused=False
        # Rendering/input time belongs to the next frame, but time spent handling
        # a pause or seek must not advance the newly selected position.
        previous=now()


def play(frames):
    original=termios.tcgetattr(sys.stdin.fileno())
    try:curses.wrapper(lambda window:player(frames,window))
    finally:
        termios.tcsetattr(sys.stdin.fileno(),termios.TCSADRAIN,original)


def main(argv=None):
    parser=argparse.ArgumentParser(prog='lk force',description='A local transmission from a galaxy far, far away.')
    parser.add_argument('--fetch',action='store_true',help='download/verify the tiny offline cache without playing')
    parser.add_argument('--status',action='store_true',help='show local cache and playback details')
    parser.add_argument('--about',action='store_true',help='show the original artist and snapshot source')
    args=parser.parse_args(argv)
    if args.about:
        print(f'Star Wars ASCIIMATION by {AUTHOR}\n{ORIGINAL}\nSnapshot: {SOURCE}\nFrames: 67 × 13; timing in fifteenths of a second.\nThe fan animation is unfinished. Playback uses a private local cache, not a Telnet server.')
        return 0
    if args.status:
        path=cache_path()
        if not path.exists():print('No local transmission yet. Run lk force or lk force --fetch.');return 0
        try:
            raw,frames=read_cache(path)
            print(json.dumps({'cached':True,'cache':str(path),'compressed_bytes':path.stat().st_size,'text_bytes':len(raw),'frames':len(frames),'seconds':timeline(frames)[-1]/TICKS_PER_SECOND,'sha256':SHA256},indent=2))
            return 0
        except (OSError,ValueError,EOFError) as error:print('Transmission unavailable: '+str(error));return 1
    if not args.fetch and not (sys.stdin.isatty() and sys.stdout.isatty()):
        print('Open lk force in a terminal, or use --fetch / --status.');return 2
    try:
        if not args.fetch and not cache_path().exists():print('Receiving a small local transmission…',flush=True)
        raw,frames=ensure_cache(refresh=args.fetch)
        if args.fetch:
            print(f'Transmission cached · {cache_path().stat().st_size:,} bytes · {len(frames):,} frames · offline ready')
            return 0
        play(frames);return 0
    except KeyboardInterrupt:return 0
    except (OSError,ValueError,EOFError,curses.error) as error:
        print('Transmission unavailable: '+str(error));return 1


if __name__=='__main__':raise SystemExit(main())
