"""Readable printer detail rows, shared by the desk and ordinary CLI output."""
import re
import shlex
import textwrap
import clipboard_shelf
from notebook_markdown import safe_text,cell_width


def option_rows(text):
    rows=[]
    for line in str(text).splitlines():
        left,separator,right=line.partition(':')
        if not separator:continue
        key,_,label=left.partition('/')
        try:choices=shlex.split(right)
        except ValueError:choices=right.split()
        defaults=[value[1:] for value in choices if value.startswith('*')]
        human=re.sub(r'(?<=[a-z])(?=[A-Z])',' ',label.strip() or key.strip()).replace('_',' ')
        rows.append({'key':key.strip(),'label':human,'default':', '.join(defaults) or 'Not reported','choices':[value.lstrip('*') for value in choices]})
    return rows


def render(view,value,width=80,colors=None):
    width=max(24,width)
    blue,muted=clipboard_shelf.command_inks(colors or {}) if colors else ('','')
    reset='\033[0m' if colors else '';ink=colors.get('WHITE',reset) if colors else ''
    lines=[]
    def line(text='',color=''):
        text=safe_text(str(text))
        wrapped=textwrap.wrap(text,width,break_long_words=False,break_on_hyphens=False,subsequent_indent='  ' if text.startswith('  ') else '') or ['']
        for paragraph in wrapped:
            for part in clipboard_shelf.wrap_cells(paragraph,width):lines.append(color+part+reset)
    def pair(label,text):
        # Aligned pairs leave a useful value column even in narrow panes.
        left=min(26,max(10,width//3));label_parts=clipboard_shelf.wrap_cells(safe_text(label),left)
        value_parts=clipboard_shelf.wrap_cells(safe_text(str(text)),max(1,width-left-2))
        for index in range(max(len(label_parts),len(value_parts))):
            key=label_parts[index] if index<len(label_parts) else ''
            val=value_parts[index] if index<len(value_parts) else ''
            lines.append(blue+key+' '*(left-sum(cell_width(character) for character in key))+reset+'  '+ink+val+reset)
    title={'options':'Printer options','jobs':'Print jobs','routes':'Printer routes'}[view]
    line(title,blue);line('─'*min(width,60),muted)
    if value.get('destination') or value.get('printer'):pair('Printer',value.get('destination') or value.get('printer'))
    if view=='options':
        if value.get('node'):pair('Via computer',value['node'])
        if value.get('queue'):pair('Queue',value['queue'])
        line();pair('Setting','Current / default')
        rows=option_rows(value.get('options',''))
        for row in rows:
            current=row['default']
            if row['key'].casefold() in {'duplex','sides'}:
                friendly={'DuplexNoTumble':'Long-edge duplex','DuplexTumble':'Short-edge duplex','None':'Single-sided','one-sided':'Single-sided','two-sided-long-edge':'Long-edge duplex','two-sided-short-edge':'Short-edge duplex'}.get(current)
                if friendly:current=friendly+' ('+current+')'
            line();pair(row['label'],current)
            choices=' · '.join(row['choices']) or 'No choices reported'
            line('  Available: '+choices,muted)
        if not rows:line('The installed driver did not report configurable options.',muted)
    else:
        routes=value.get('routes',[])
        if not routes:line('No routes or jobs reported.',muted)
        for index,row in enumerate(routes):
            line();line('Route '+str(index+1),blue)
            pair('Computer',row.get('node','local'))
            pair('Queue',row.get('name') or row.get('queue',''))
            if row.get('error'):pair('Unavailable',row['error']);continue
            if view=='routes':
                pair('Status',row.get('status','Not reported'))
                pair('Profile',row.get('profile',{}).get('kind','document'))
                if row.get('device',{}).get('source'):pair('Identity',row['device']['source'])
            else:
                jobs=str(row.get('jobs','')).splitlines()
                if not jobs:line('  No queued/recent jobs reported.',muted)
                for job in jobs:
                    fields=re.split(r'\s+',job.strip(),maxsplit=3)
                    line()
                    for label,text in zip(('Job','Owner','Bytes','Submitted'),fields):pair(label,text)
    return lines
