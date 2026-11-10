"""Read-only command discovery; selection edits the shell, never executes a tool."""
import contextlib
import io
import json
import re
import shutil
import sys
import termios
import textwrap
import tty
from pathlib import Path


def groups(rows):
    result={}
    for row in rows:
        words=row[0].split()
        if len(words)>1 and words[0]=='lk' and not words[1].startswith(('[','<','-','_')):
            result.setdefault(words[1],[]).append(row)
    return dict(sorted(result.items()))


def forms(rows):
    """Expose simple leading alternatives without inventing argument grammars."""
    result=[]
    for template,category,description in rows:
        match=re.match(r'^(lk \S+) \[([^\[\]]+\|[^\[\]]+)\](.*)$',template)
        if match:
            for choice in match[2].split('|'):
                result.append((match[1]+' '+choice+match[3],category,description))
        result.append((template,category,description))
    return list(dict.fromkeys(result))


def help_lines(name,width):
    try:data=json.loads((Path(__file__).with_name('docs')/'command_help.json').read_text())
    except (OSError,ValueError):data={}
    text=data.get(name,'No extended help available. Command forms are shown in the previous view.')
    return [part for line in text.splitlines() for part in (textwrap.wrap(line,max(1,width)) or [''])]


def run(ui):
    import clipboard_shelf,terminal_style
    catalog=groups(ui._command_rows())
    if not (sys.stdin.isatty() and sys.stdout.isatty()):
        for name,rows in catalog.items():
            for template,category,description in forms(rows):print(f'{template} · {description}')
        return 0
    # Capture once: redraws must not repeat network probes or change the artwork.
    welcome=[]
    if hasattr(ui,'home'):
        buffer=io.StringIO()
        with contextlib.redirect_stdout(buffer):ui.home()
        welcome=buffer.getvalue().rstrip().splitlines()
    fd=sys.stdin.fileno();old=termios.tcgetattr(fd)
    selected=None;query='';index=0;details=False
    try:
        tty.setcbreak(fd)
        while True:
            size=shutil.get_terminal_size((100,30));width=max(1,size.columns-1)
            colors=terminal_style.list_colors()
            blue,muted=clipboard_shelf.command_inks(colors)
            light=terminal_style.luminance(colors.get('_palette',{}).get('background','#111111'))>.3
            brass='\033[38;2;126;91;34m' if light else '\033[38;2;214;179;106m'
            reset='\033[0m'
            hints=clipboard_shelf.command_rows([('Type','search'),('↑↓','choose'),('PgUp/PgDn','page'),
                ('Home/End','first/last'),('Enter','back' if details else 'edit command' if selected else 'browse'),
                ('Tab','options/help'),('Esc/←','back'),('Ctrl-Q','quit')],width,colors)
            header=welcome if not selected and len(welcome)<=size.lines-len(hints)-12 else []
            height=max(1,size.lines-len(hints)-4-len(header))
            rows=forms(catalog[selected]) if selected else [('lk '+name,rows[0][1],rows[0][2]) for name,rows in catalog.items()]
            visible=[r for r in rows if all(t in ' '.join(r).casefold() for t in query.casefold().split())]
            lines=help_lines(selected,width) if details else visible
            index=min(index,max(0,len(lines)-1));top=max(0,index-height+1)
            print('\033[2J\033[H',end='')
            for n,line in enumerate(header):
                ink=brass if n==0 else muted
                line=re.sub(r'\blk(?: home| o)?\b|\blo\b',lambda m:blue+m[0]+ink,line)
                print(ui._ansi_clip(ink+line+reset,width))
            print(ui._ansi_clip(brass+'LOOK COMMANDS'+muted+(' · '+selected if selected else ' · l opens files')+reset,width))
            for n,row in enumerate(lines[top:top+height],top):
                if details:print(row)
                else:
                    mark='› ' if n==index else '  '
                    emphasis='\033[1m' if n==index else ''
                    text=emphasis+blue+mark+row[0]+reset+muted+'  · '+row[2]+reset
                    print(ui._ansi_clip(text,width))
            print(ui._ansi_clip(blue+'FILTER '+muted+query+reset,width) if not details else blue+'OPTIONS / HELP'+muted+' · read only'+reset)
            print('\n'.join(hints),end='',flush=True)
            key=ui._read_tty_key(fd)
            if key in {'\x11','\x03'}:break
            if key in {'esc','left'}:
                if query:query=''
                elif details:details=False
                elif selected:selected=None
                else:break
                index=0;continue
            if key in {'up','down','pageup','pagedown','shiftup','shiftdown','home','end','shiftleft','shiftright'}:
                if key in {'home','shiftleft'}:index=0
                elif key in {'end','shiftright'}:index=max(0,len(lines)-1)
                else:index=max(0,min(len(lines)-1,index+({'up':-1,'down':1,'pageup':-height,'shiftup':-height,'pagedown':height,'shiftdown':height}[key])))
                continue
            if key=='\t' and visible:
                if not selected:selected=visible[index][0].split()[1]
                details=True;index=0;query='';continue
            if key in {'\r','\n','right'}:
                if details:details=False;index=0;continue
                if not visible:continue
                if selected:ui._write_command_request(visible[index][0]);break
                selected=visible[index][0].split()[1];index=0;query='';continue
            if not details:
                if key in {'\x7f','\b'}:query=query[:-1];index=0
                elif len(key)==1 and key.isprintable():query+=key;index=0
    finally:
        termios.tcsetattr(fd,termios.TCSADRAIN,old);print('\033[2J\033[H',end='',flush=True)
    return 0
