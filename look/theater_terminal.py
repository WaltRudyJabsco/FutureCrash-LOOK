"""Keyboard projection room, using the shared Theater and Print pipelines."""
from __future__ import annotations
import base64
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
import termios
import time
import tty

import clipboard_shelf
from notebook_markdown import safe_text
import terminal_style
from theater_desk import request


def default_host():
    for name in ('theater','media_storage'):
        try:
            value=json.loads((Path.home()/f'.config/look/{name}.json').read_text())
            if value.get('node'):return value['node']
        except (OSError,ValueError):pass
    return 'local'


def ticket_file():
    return Path.home()/'.local/share/look/theater/tickets.json'


def saved_tickets():
    path=ticket_file()
    if path.is_symlink():raise ValueError('Ticket storage must be a regular file')
    try:return json.loads(path.read_text())
    except FileNotFoundError:return {}


def remember(node,ticket):
    """Codes are secrets, so keep an owner-only local copy for later QR printing."""
    path=ticket_file();path.parent.mkdir(parents=True,exist_ok=True,mode=0o700)
    tickets=saved_tickets();tickets.setdefault(node,{})[ticket['id']]=ticket
    fd,temp=tempfile.mkstemp(prefix='.tickets-',dir=path.parent)
    try:
        with os.fdopen(fd,'w') as stream:json.dump(tickets,stream)
        os.replace(temp,path)
    finally:
        if os.path.exists(temp):os.unlink(temp)


def print_ticket(ticket,node,ui,queue=None):
    """Generate the issued ticket's QR and use Print's existing preview/send flow."""
    import printing
    data=request({'action':'qr','code':ticket['code']},node)
    raw=base64.b64decode(data['png'],validate=True)
    if not raw.startswith(b'\x89PNG\r\n\x1a\n'):raise ValueError('The host did not return a PNG ticket')
    with tempfile.TemporaryDirectory(prefix='look-theater-ticket-') as directory:
        path=Path(directory)/'Theater ticket.png';path.write_bytes(raw)
        caption=[ticket.get('title') or 'Fabric Theater',ticket['code'],
                 'Valid until '+time.strftime('%b %d, %Y %H:%M',time.localtime(ticket['expires']))]
        # QR modules remain square: image style and the shared raster renderer own scaling.
        return printing.selected_file(path,ui,prefer_receipt=True,default_style='image',caption=caption,queue=queue)


class Desk:
    def __init__(self,ui,node=None):
        self.ui=ui;self.node=node or default_host();self.movie=None
        self.state={};self.notice=''

    def call(self,value):
        print('\r\033[K'+safe_text('Theater · '+self.node+' · working…'),end='',flush=True)
        return request(value,self.node)

    def refresh(self):
        self.state=self.call({'action':'status'})

    def choose(self,title,rows,details=()):
        """One raw-key boundary shared by every menu, restored before print/prompts."""
        fd=sys.stdin.fileno();prior=termios.tcgetattr(fd);selected=0;last=None
        try:
            tty.setcbreak(fd)
            current=termios.tcgetattr(fd);current[0]&=~termios.IXON
            termios.tcsetattr(fd,termios.TCSANOW,current)
            while True:
                width,height=shutil.get_terminal_size((90,28));width=max(20,width-1)
                colors=terminal_style.list_colors()
                footer=clipboard_shelf.command_rows([('↑↓','choose'),('Enter','select'),('PgUp/PgDn','page'),('Home/End','first/last'),('q/Esc','back'),('Ctrl-Q','quit')],width,colors)
                header=[self.ui._c('FABRIC THEATER','1;34'),safe_text(title)]
                header += [' '.join(safe_text(str(line)).split()) for line in details]
                page=max(1,height-len(header)-len(footer)-2)
                selected=max(0,min(selected,len(rows)-1));start=max(0,min(selected-page//2,max(0,len(rows)-page)))
                lines=header+['']
                for i,(label,value) in list(enumerate(rows))[start:start+page]:
                    text=('› ' if i==selected else '  ')+' '.join(safe_text(str(label)).split())
                    text=self.ui._ansi_clip(text,width)
                    lines.append(self.ui._c(text,'1;34') if i==selected else text)
                frame='\033[H'+'\n'.join(self.ui._ansi_clip(line,width)+'\033[K' for line in lines+['']+footer)+'\033[J'
                if frame!=last:sys.stdout.write(frame);sys.stdout.flush();last=frame
                key=self.ui._read_tty_key(fd,.2)
                if key in ('\x11','\x03'):raise KeyboardInterrupt
                if key in ('q','Q','esc','\x1b'):return None
                if key in ('enter','\r','\n') and rows:return rows[selected][1]
                if key in ('up','\x1b[A','k'):selected=max(0,selected-1)
                elif key in ('down','\x1b[B','j','\t'):selected=min(len(rows)-1,selected+1)
                elif key in ('pageup','\x1b[5~','shiftup','\x1b[1;2A'):selected=max(0,selected-page)
                elif key in ('pagedown','\x1b[6~','shiftdown','\x1b[1;2B'):selected=min(len(rows)-1,selected+page)
                elif key in ('home','\x1b[H','\x1b[1~','shiftleft','\x1b[1;2D'):selected=0
                elif key in ('end','\x1b[F','\x1b[4~','shiftright','\x1b[1;2C'):selected=len(rows)-1
        finally:termios.tcsetattr(fd,termios.TCSADRAIN,prior)

    def prompt(self,label,initial=''):
        from look_renderer import prompt_line
        sys.stdout.write('\033[2J\033[H');sys.stdout.flush()
        value,cancelled=prompt_line(label,initial=initial)
        return None if cancelled else value.strip()

    def pick_movie(self):
        query=self.prompt('Find a movie (Enter browses this host): ')
        while query is not None:
            result=self.call({'action':'search','query':query,'kind':'video'})
            movies=[r for r in result['items'] if str(r.get('media_type','')).startswith('video/')]
            rows=[('Search again…','search')]+[(r.get('title') or r['id'],r) for r in movies]
            picked=self.choose('Movies on '+self.node,rows,[str(len(movies))+' results · narrow the search to find more'])
            if picked=='search':query=self.prompt('Find a movie: ',query);continue
            if picked:self.movie=picked;self.notice='Selected '+picked.get('title',picked['id'])
            return

    def host(self):
        import fabric_files
        data=fabric_files.request('/v1/nodes')
        names=['local',*[r['name'] for r in data.get('peers',[]) if r.get('trusted')]]
        selected=self.choose('Choose the computer that owns the movies',[(name,name) for name in names])
        if selected:
            self.node=selected;self.movie=None
            path=Path.home()/'.config/look/theater.json';path.parent.mkdir(parents=True,exist_ok=True)
            path.write_text(json.dumps({'node':selected}))
            self.refresh()

    def issue(self,channel=False):
        if not channel and not self.movie:self.pick_movie()
        if not channel and not self.movie:return
        hours=self.choose('Ticket lifetime',[('One hour',1),('One day',24),('Five days',120),('One week',168)])
        if hours is None:return
        value={'action':'ticket','scope':'channel' if channel else 'movie','hours':hours}
        if not channel:value['media']=self.movie['id']
        ticket=self.call(value)
        remember(self.node,ticket)
        self.refresh()
        self.ticket(ticket)

    def ticket(self,ticket):
        while True:
            action=self.choose('Admission · '+ticket.get('title','Theater'),[
                ('Print QR on Little Printer','little'),('Print QR · choose another printer','print'),
                ('Copy ticket link','copy'),('Open audience page','open'),('Back','back')],
                [ticket['url'],'Code '+ticket['code'],'Expires '+time.strftime('%b %d, %H:%M',time.localtime(ticket['expires']))])
            if action in (None,'back'):return
            try:
                if action in {'little','print'}:
                    print_ticket(ticket,self.node,self.ui,'Little Printer' if action=='little' else None)
                    self.notice='Returned from print preview'
                elif action=='copy':
                    self.notice='Ticket link copied' if clipboard_shelf.copy_clipboard(ticket['url']) else 'System clipboard unavailable; the ticket link is shown above'
                elif action=='open':
                    import webbrowser
                    webbrowser.open(ticket['url']);self.notice='Opened audience page'
            except (OSError,ValueError,RuntimeError) as exc:self.notice=str(exc)
            if self.notice:self.choose(self.notice,[('Return to ticket',True)])

    def tickets(self):
        self.refresh()
        rows=self.state.get('tickets',[])
        selected=self.choose('Tickets on '+self.node,[(r.get('title','Theater')+' · '+('revoked' if r['revoked'] else 'expired' if r['expires']<=time.time() else time.strftime('%b %d %H:%M',time.localtime(r['expires']))),r) for r in rows])
        if not selected:return
        local=saved_tickets().get(self.node,{}).get(selected['id'])
        active=not selected['revoked'] and selected['expires']>time.time()
        choices=[]
        if local and active:choices.append(('View / print issued ticket','view'))
        if active:choices.append(('Revoke this ticket','revoke'))
        choices.append(('Back','back'))
        action=self.choose(selected.get('title','Theater'),choices,[] if local else ['The link/code is available only where this ticket was issued.'])
        if action=='view':self.ticket(local)
        elif action=='revoke':self.call({'action':'revoke','id':selected['id']});self.notice='Ticket revoked'

    def run(self):
        sys.stdout.write('\033[?1049h\033[2J');sys.stdout.flush()
        try:
            try:self.refresh()
            except (OSError,ValueError) as exc:self.notice=str(exc)
            while True:
                channel=self.state.get('channel',{});paused=channel.get('state')=='paused'
                details=[self.node+' · '+(channel.get('title') or 'Between showings')+' · '+channel.get('state','stopped'),
                         'Selected movie · '+(self.movie or {}).get('title','Choose a movie'),self.notice]
                action=self.choose('Projection room',[
                    ('Choose a movie','movie'),('Start showing selected movie','show'),
                    ('Resume showing' if paused else 'Pause showing','resume' if paused else 'pause'),
                    ('Seek to a time','seek'),('End showing','stop'),('Create movie ticket','ticket'),
                    ('Create channel ticket','channel'),('Manage issued tickets','tickets'),
                    ('Choose media host','host'),('Refresh','refresh'),('Quit','quit')],details)
                if action in (None,'quit'):return 0
                self.notice=''
                try:
                    if action=='movie':self.pick_movie()
                    elif action=='host':self.host()
                    elif action=='ticket':self.issue()
                    elif action=='channel':self.issue(channel=True)
                    elif action=='tickets':self.tickets()
                    elif action=='refresh':self.refresh()
                    elif action=='show':
                        if not self.movie:self.pick_movie()
                        if self.movie:self.call({'action':'show','media':self.movie['id']});self.refresh()
                    elif action=='seek':
                        value=self.prompt('Go to time MM:SS (or seconds): ')
                        if value:
                            parts=value.split(':');seconds=float(parts[-1])+(float(parts[0])*60 if len(parts)==2 else 0)
                            if len(parts)>2:raise ValueError('Use MM:SS or seconds')
                            self.call({'action':'seek','position':seconds});self.refresh()
                    else:self.call({'action':action});self.refresh()
                except (OSError,ValueError,RuntimeError) as exc:self.notice=str(exc)
        except (KeyboardInterrupt,EOFError):return 0
        finally:
            sys.stdout.write('\033[0m\033[?1049l');sys.stdout.flush()
