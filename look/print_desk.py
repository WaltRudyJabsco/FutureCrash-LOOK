"""Small physical-printer desk; selections never submit a print job."""
import sys
import termios
import tty
import clipboard_shelf
import printing
import print_details
from notebook_markdown import safe_text


def screen(ui,select=False,node='auto'):
    if ui is None:raise ValueError('Open the printer desk through lk print')
    fd=sys.stdin.fileno();old=termios.tcgetattr(fd);selected=0;detail=None;notice='';offset=0
    def refresh():
        value=printing.destinations()
        rows=value.get('printers',[])
        if node!='auto':
            owner=value.get('local_node') if node=='local' else node
            rows=[dict(row,routes=[route for route in row['routes'] if route['node']==owner]) for row in rows]
            rows=[row for row in rows if row['routes']]
        return rows,value.get('errors',[])
    try:
        tty.setcbreak(fd)
        sys.stdout.write('\x1b[2J\x1b[HLOOK PRINT · finding printers…');sys.stdout.flush()
        rows,errors=refresh()
        while True:
            width,height=ui.shutil.get_terminal_size((100,30));width=max(24,width);height=max(10,height)
            selected=max(0,min(selected,max(0,len(rows)-1)));chosen=rows[selected] if rows else None
            hints=[('↑↓','choose'),('Tab','next'),('Enter','select' if select else 'options')]
            if not select:hints += [('o','options'),('j','jobs'),('r','routes'),('n','nickname'),('R','refresh')]
            hints += [('PgUp/PgDn','scroll'),('q/Esc','back' if detail else 'close')]
            if detail:hints=[('↑↓','scroll'),('PgUp/PgDn','page'),('q/Esc','back')]
            footer=clipboard_shelf.command_rows(hints,width,ui.terminal_style.list_colors())
            frame=[ui._c('LOOK PRINT','1;36')+' · '+('Choose a printer' if select else 'Printers')]
            if detail:
                page=max(1,height-len(footer)-3)
                lines=print_details.render(detail[0],detail[1],width,ui.terminal_style.list_colors())
                offset=max(0,min(offset,max(0,len(lines)-page)));frame+=lines[offset:offset+page]
            else:
                page=max(1,height-len(footer)-3);top=max(0,selected-page+1)
                for index,row in enumerate(rows[top:top+page],top):
                    label=row['label']+' · '+str(len(row['routes']))+' route'+('s' if len(row['routes'])!=1 else '')
                    if not row.get('identity_verified'):label+=' · identity unverified'
                    frame.append(ui.terminal_style.list_row(safe_text(label),width,index,index==selected,ui.terminal_style.list_colors()))
                if not rows:frame.append('No configured printers visible. Use system printer settings or lk print discover.')
            message=notice or ('Read-only details; printer defaults remain in system settings.' if detail else 'Some owners/spoolers unavailable; list may be incomplete.' if errors else 'Select a printer; queues are managed underneath. Nothing prints here.')
            frame+=['']*max(0,height-len(footer)-len(frame)-1);frame+=footer+[safe_text(message)]
            sys.stdout.write(ui._terminal_frame_payload('\n'.join(ui._ansi_clip(line,width) for line in frame)));sys.stdout.flush()
            key=ui._read_tty_key(fd)
            if key in {'q','esc','\x03','\x04'}:
                if detail:detail=None;offset=0;continue
                return None
            if detail:
                if key in {'down','pagedown','shiftdown'}:offset+=1 if key=='down' else page
                if key in {'up','pageup','shiftup'}:offset-=1 if key=='up' else page
                continue
            if key in {'down','\t'}:selected=(selected+1)%len(rows) if rows else 0
            elif key=='up':selected=max(0,selected-1)
            elif key in {'pagedown','shiftdown'}:selected+=page
            elif key in {'pageup','shiftup'}:selected-=page
            elif key in {'home','shiftleft'}:selected=0
            elif key in {'end','shiftright'}:selected=len(rows)-1
            elif key=='R':rows,errors=refresh();notice='Refreshed'
            elif chosen and key in {'enter','\r','\n','o','j','r','n'}:
                if select and key in {'enter','\r','\n'}:return chosen
                try:
                    if key=='r':detail=('routes',{'printer':chosen['label'],'routes':chosen['routes']})
                    elif key=='n':
                        from look_renderer import prompt_line
                        termios.tcsetattr(fd,termios.TCSADRAIN,old)
                        try:
                            label,cancelled=prompt_line('Nickname for '+chosen['label']+': ')
                            if not cancelled and label.strip():
                                answer,cancelled=prompt_line('Set “'+label.strip()+'” on this printer’s reachable routes? [y/N] ')
                                if not cancelled and answer.casefold()=='y':
                                    result=printing.request('nickname','auto',queue=chosen['id'],label=label.strip(),confirm=True)
                                    notice='Nickname updated' if not any(row.get('error') for row in result['routes']) else 'Some routes failed to update; inspect Routes and retry'
                                    rows,errors=refresh()
                        finally:tty.setcbreak(fd)
                    else:
                        value=printing.request('jobs' if key=='j' else 'options','auto',queue=chosen['id'])
                        detail=('jobs' if key=='j' else 'options',value)
                    offset=0
                except (OSError,ValueError,RuntimeError) as error:notice=str(error)
    finally:
        termios.tcsetattr(fd,termios.TCSADRAIN,old)
        sys.stdout.write('\x1b[0m\x1b[2J\x1b[H');sys.stdout.flush()


def pick(ui,node='auto'):return screen(ui,select=True,node=node)
def desk(ui):screen(ui);return 0
