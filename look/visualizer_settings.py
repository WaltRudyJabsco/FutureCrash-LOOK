"""One per-user visualizer selection shared by LOOK's terminal players."""
from pathlib import Path
import json
import sys
import termios
import time
import tty
import book_reader
import player_visuals
import terminal_style
from notebook_markdown import safe_text

SCHEMA=1
REFRESH_SECONDS=1.0
MAX_SETTINGS_BYTES=65536
_cached=None
_checked=0.0
_cached_path=None
_warning=''


def path():return Path.home()/'.config/look/visualizers.json'


def read():
    try:
        with path().open('rb') as source:raw=source.read(MAX_SETTINGS_BYTES+1)
    except FileNotFoundError:return {'schema':SCHEMA,'disabled':[]}
    if len(raw)>MAX_SETTINGS_BYTES:raise ValueError('Visualizer settings exceed 64 KiB')
    value=json.loads(raw)
    if not isinstance(value,dict) or value.get('schema')!=SCHEMA:raise ValueError('Unsupported visualizer settings')
    disabled=value.get('disabled',[])
    if not isinstance(disabled,list) or len(disabled)>128 or any(not isinstance(name,str) or len(name)>100 for name in disabled):raise ValueError('Invalid disabled visualizer list')
    return dict(value,disabled=disabled)


def save(disabled):
    try:value=read()
    except (OSError,ValueError):value={'schema':SCHEMA}
    value['disabled']=sorted(set(disabled))
    book_reader.write_json(path(),value)
    enabled_modes(refresh=True)


def enabled_modes(*,refresh=False):
    global _cached,_checked,_cached_path,_warning
    now=time.monotonic();current=path()
    if not refresh and _cached_path==current and _cached is not None and 0<=now-_checked<REFRESH_SECONDS:return _cached
    try:disabled=set(read()['disabled']);_warning=''
    except (OSError,ValueError) as exc:disabled=set();_warning='Visualizer settings unreadable · V opens repair: '+str(exc)
    _cached=tuple(i for i,name in enumerate(player_visuals.NAMES[:-1],1) if name not in disabled)
    _cached_path=current;_checked=now
    return _cached


def warning():return _warning


def picker(ui,fd=None):
    """Space stages toggles; Enter saves atomically; Escape leaves settings intact."""
    if not (sys.stdin.isatty() and sys.stdout.isatty()):
        enabled=set(enabled_modes(refresh=True))
        for i,name in enumerate(player_visuals.NAMES[:-1],1):print(('[x] ' if i in enabled else '[ ] ')+name)
        return False
    fd=sys.stdin.fileno() if fd is None else fd;old=termios.tcgetattr(fd)
    names=player_visuals.NAMES[:-1];index=0;notice='Shared by player, MP and TV · normal view is always available'
    try:disabled=set(read()['disabled'])
    except (OSError,ValueError):disabled=set();notice='Settings unreadable · Enter replaces them with this selection; Esc keeps the file'
    last=None
    try:
        tty.setcbreak(fd)
        sys.stdout.write('\033[?25l')
        while True:
            width,height=ui.shutil.get_terminal_size((80,28));width=max(20,width)
            controls=ui._media_hints('↑↓ move · Shift-arrows page/ends · Space toggle · a all · n none · Enter save · Esc cancel',width).splitlines()
            controls=controls[:max(1,height-5)];page=max(1,height-len(controls)-5)
            index=max(0,min(index,len(names)-1));top=(index//page)*page
            count=sum(name not in disabled for name in names)
            frame=[ui._c('VISUALIZERS','1;36')+f' · {count}/{len(names)} enabled',
                   ui._c('v and ten-second Cycle both use this selection','2')]
            colors=terminal_style.list_colors()
            for position,name in enumerate(names[top:top+page],top):
                prefix=('› ' if position==index else '  ')+('[ ] ' if name in disabled else '[x] ')
                line=ui._c(prefix,'33')+ui._c(name,'37' if name not in disabled else '2')
                frame.append(terminal_style.list_row(line,width,position,position==index,colors))
            frame+=['']*max(0,page+2-len(frame))
            frame += [ui._c('No visuals selected · v stays in normal view' if not count and not notice.startswith('Could not save') else safe_text(notice),'33'),*controls]
            rendered=ui._terminal_frame_payload('\n'.join(ui._ansi_clip(line,width) for line in frame))
            identity=(width,height,rendered)
            if identity!=last:sys.stdout.write(rendered);sys.stdout.flush();last=identity
            key=ui._read_tty_key(fd,.2)
            if not key:continue
            if key in {'esc','q','\x03'}:return False
            if key=='up':index-=1
            elif key=='down':index+=1
            elif key in {'shiftup','pageup'}:index-=page
            elif key in {'shiftdown','pagedown'}:index+=page
            elif key in {'home','shiftleft'}:index=0
            elif key in {'end','shiftright'}:index=len(names)-1
            elif key==' ':
                if names[index] in disabled:disabled.remove(names[index])
                else:disabled.add(names[index])
            elif key=='a':disabled.difference_update(names)
            elif key=='n':disabled.update(names)
            elif key in {'enter','\r','\n'}:
                try:save(disabled);return True
                except (OSError,ValueError) as exc:notice='Could not save: '+str(exc)
    finally:
        termios.tcsetattr(fd,termios.TCSADRAIN,old)
        sys.stdout.write('\033[?25h\033[0m');sys.stdout.flush()
