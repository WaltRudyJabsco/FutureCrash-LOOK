"""Small artist/album views over the same catalog used by Media Find."""
from __future__ import annotations
import shutil
import sys
import termios
import tty


def groups(entries,field):
    result={}
    for row in entries:
        if str(row.get('media_type') or '').startswith('video/') or row.get('kind')=='video': continue
        album=str(row.get('album') or 'Unknown album').strip()
        artist=str(row.get('album_artist') or row.get('artist') or 'Unknown artist').strip()
        key=(artist.casefold(),album.casefold()) if field=='album' else (artist.casefold(),)
        item=result.setdefault(key,{'label':album+' · '+artist if field=='album' else artist,'entries':[]})
        item['entries'].append(row)
    def order(row):
        return (int(row.get('disc') or 1),int(row.get('track') or 0),str(row.get('title') or '').casefold())
    for item in result.values(): item['entries'].sort(key=order)
    return sorted(result.values(),key=lambda item:item['label'].casefold())


def choose(items,title,read_key,hints):
    fd=sys.stdin.fileno(); old=termios.tcgetattr(fd); query=''; index=0
    try:
        tty.setcbreak(fd); sys.stdout.write('\033[?25l')
        while True:
            visible=[item for item in items if all(word in item['label'].casefold() for word in query.casefold().split())]
            index=max(0,min(index,max(0,len(visible)-1)))
            width,height=shutil.get_terminal_size((100,30)); page=max(1,height-5); top=max(0,index-page+1)
            frame=['\033[1;38;5;117m'+title+'\033[0m · '+str(len(visible))+' shown','']
            for n,item in enumerate(visible[top:top+page],top):
                line=('› ' if n==index else '  ')+item['label']+' · '+str(len(item['entries']))+' tracks'
                frame.append(('\033[1;38;5;117m' if n==index else '')+line[:max(1,width-1)]+'\033[0m')
            frame.extend(['']*max(0,height-3-len(frame)))
            frame.extend(['FILTER '+query+'█',hints('↑↓ move · Enter open · Shift-arrows page/ends · Esc clear/back',width)])
            sys.stdout.write('\033[2J\033[H'+'\n'.join(frame)+'\033[J');sys.stdout.flush()
            key=read_key(fd,None)
            if key in {'esc','q','\x03'}:
                if key=='esc' and query: query=''; index=0;continue
                return None
            if key in {'\r','\n','enter'} and visible: return visible[index]
            if key in {'up','K'}: index-=1
            elif key in {'down','J'}: index+=1
            elif key in {'pageup','shiftup'}: index-=page
            elif key in {'pagedown','shiftdown'}: index+=page
            elif key in {'home','shiftleft'}: index=0
            elif key in {'end','shiftright'}: index=len(visible)-1
            elif key in {'\x7f','\b'}: query=query[:-1];index=0
            elif len(key)==1 and key.isprintable():query+=key;index=0
    finally:
        termios.tcsetattr(fd,termios.TCSADRAIN,old);sys.stdout.write('\033[?25h\033[0m');sys.stdout.flush()


def browse(entries,field,query,read_key,hints,open_tracks):
    items=groups(entries,field)
    if query:items=[item for item in items if query.casefold() in item['label'].casefold()]
    while True:
        selected=choose(items,'FABRIC MEDIA · '+('ALBUMS' if field=='album' else 'ARTISTS'),read_key,hints)
        if selected is None:return None
        if field=='artist':
            result=browse(selected['entries'],'album','',read_key,hints,open_tracks)
        else:result=open_tracks(selected['entries'],selected['label'])
        if result is not None:return result
