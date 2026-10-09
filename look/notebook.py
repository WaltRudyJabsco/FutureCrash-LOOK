"""LOOK notebook commands, terminal workspace, and LO tools."""
from __future__ import annotations
import argparse
import datetime as dt
import json
import os
import re
from pathlib import Path
import shlex
import shutil
import subprocess
import sys
import termios
import textwrap
import time
import tty
import urllib.request

try:
    from .notebook_core import Notebook, timestamp
except ImportError:
    from notebook_core import Notebook, timestamp


def daemon(action,payload=None,timeout=10):
    path='/v1/notebook/'+action
    data=json.dumps(payload).encode() if payload is not None else None
    with urllib.request.urlopen(urllib.request.Request('http://127.0.0.1:7332'+path,data=data,
            headers={'Content-Type':'application/json'}),timeout=timeout) as response:
        result=json.load(response)
    if not result.get('ok',True): raise RuntimeError(result.get('error') or 'Notebook request failed')
    return result


def nudge_sync():
    # Local capture is already durable; node synchronization must not delay typing.
    try: daemon('wake',{},timeout=.5)
    except (OSError,ValueError): pass


def local_target(target):
    if target != 'local':
        return ','.join(part.strip() for part in target.split(',') if part.strip()) or 'all'
    try:
        with urllib.request.urlopen('http://127.0.0.1:7332/v1/identity',timeout=.5) as response:
            return json.load(response)['identity']['name']
    except (OSError,ValueError,KeyError):
        raise ValueError('Local targeting needs the node daemon; use its explicit node name offline')


def edit(store,row):
    editor=shlex.split(os.environ.get('VISUAL') or os.environ.get('EDITOR') or ('nvim' if shutil.which('nvim') else 'vi'))
    subprocess.run([*editor,row['path']],check=True)
    store.snapshot()
    nudge_sync()


def display(row):
    due=dt.datetime.fromtimestamp(row['remind_at'] or row['due']).strftime('%a %b %d %H:%M') if row.get('remind_at') or row.get('due') else ''
    return f"{row['id'][:8]} · {row['kind']} · {row['project']} · {row['title']}"+(' · '+due if due else '')+(' · CONFLICT' if row['conflict'] else '')


def capture_note(fd,read_key):
    """Keep Enter fast; request distinct modified keys while the note editor owns input."""
    previous=termios.tcgetattr(fd)
    text=''; cursor=0
    try:
        tty.setraw(fd)
        sys.stdout.write('\033[>1u')
        while True:
            width,height=shutil.get_terminal_size((100,30))
            before=text[:cursor]; after=text[cursor:]
            rows=(before+'█'+after).split('\n')
            rows=[part for line in rows for part in (textwrap.wrap(line,max(1,width-1),replace_whitespace=False,drop_whitespace=False) or [''])]
            cursor_row=next((index for index,line in enumerate(rows) if '█' in line),0)
            top=max(0,cursor_row-max(1,height-4)+1)
            visible=rows[top:top+max(1,height-4)]
            frame=['NEW NOTE · Enter save · Shift-Enter/Ctrl-J newline · Esc cancel'[:max(1,width-1)],'']
            frame.extend(visible)
            sys.stdout.write('\033[2J\033[H'+'\r\n'.join(frame)+'\033[J'); sys.stdout.flush()
            key=read_key(fd,None)
            if key in {'esc','\x03'}: return None
            if key in {'\r','enter'}: return text
            if key in {'shiftenter','\n'}:
                text=text[:cursor]+'\n'+text[cursor:]; cursor+=1
            elif key in {'\x7f','\b'} and cursor:
                text=text[:cursor-1]+text[cursor:]; cursor-=1
            elif key=='left': cursor=max(0,cursor-1)
            elif key=='right': cursor=min(len(text),cursor+1)
            elif key=='home': cursor=text.rfind('\n',0,cursor)+1
            elif key=='end':
                next_line=text.find('\n',cursor); cursor=len(text) if next_line<0 else next_line
            elif len(key)==1 and key.isprintable():
                text=text[:cursor]+key+text[cursor:]; cursor+=1
    finally:
        sys.stdout.write('\033[<u'); sys.stdout.flush()
        termios.tcsetattr(fd,termios.TCSADRAIN,previous)


def workspace(store,kind,read_key,hints):
    fd=sys.stdin.fileno(); old=termios.tcgetattr(fd)
    query=''; index=0; marked=set(); notice=''
    def prompt(label):
        termios.tcsetattr(fd,termios.TCSADRAIN,old)
        sys.stdout.write('\033[?25h'); sys.stdout.flush()
        try: return input('\n'+label+' › ')
        finally:
            tty.setcbreak(fd)
            sys.stdout.write('\033[?25l'); sys.stdout.flush()
    try:
        tty.setcbreak(fd)
        sys.stdout.write('\033[2J\033[H\033[?25l'); sys.stdout.flush()
        while True:
            rows=store.list(query,kind)
            index=max(0,min(index,max(0,len(rows)-1)))
            width,height=shutil.get_terminal_size((100,30)); usable=max(2,height-7)
            top=max(0,index-usable+1)
            lines=['\033[1;36mLOOK NOTEBOOK\033[0m · '+(kind or 'all')+f' · {len(rows)} shown · {len(marked)} marked','']
            for number,row in enumerate(rows[top:top+usable],top):
                marker='✓' if row['id'] in marked else ' '
                lines.append(('\033[1;36m›' if number==index else ' ')+marker+' '+display(row)[:max(10,width-5)]+'\033[0m')
            while len(lines)<height-4: lines.append('')
            lines.extend(['FILTER '+query+'█',hints('↑↓ move · Shift-arrows page/ends · Tab mark · A all · Enter edit · N new · P file · C done · R remind · D delete · / filter · Esc clear/exit',width),notice])
            sys.stdout.write('\033[H'+ '\033[K\n'.join(lines)+'\033[K\033[J'); sys.stdout.flush()
            key=read_key(fd,1)
            if not key: continue
            notice=''; chosen=[row for row in rows if row['id'] in marked] or rows[index:index+1]
            if key=='\x03' or (key=='q' and not query): break
            if key=='esc':
                if query: query=''; index=0; continue
                break
            if key in {'up','K'}: index=max(0,index-1); continue
            if key in {'down','J'}: index=min(len(rows)-1,index+1); continue
            if key in {'pageup','shiftup'}: index=max(0,index-usable); continue
            if key in {'pagedown','shiftdown'}: index=min(len(rows)-1,index+usable); continue
            if key in {'home','shiftleft'}: index=0; continue
            if key in {'end','shiftright'}: index=len(rows)-1; continue
            if key=='\t' and rows:
                identity=rows[index]['id']
                if identity in marked: marked.remove(identity)
                else: marked.add(identity)
                index=min(len(rows)-1,index+1); continue
            if key=='A':
                ids={row['id'] for row in rows}
                if ids.issubset(marked): marked-=ids
                else: marked|=ids
                continue
            try:
                if key in {'\r','\n'} and rows:
                    termios.tcsetattr(fd,termios.TCSADRAIN,old)
                    try: edit(store,rows[index])
                    finally: tty.setcbreak(fd)
                elif key=='N':
                    text=capture_note(fd,read_key)
                    if text and text.strip():
                        remind=timestamp(prompt('remind when')) if kind=='reminder' else None
                        store.create(text,kind=kind or 'note',remind_at=remind); nudge_sync()
                elif key in {'C','D','R','P'} and chosen:
                    if key=='D' and prompt(f'Delete {len(chosen)} record(s)? Type yes')!='yes': continue
                    remind=timestamp(prompt('remind when')) if key=='R' else None
                    project=prompt('file under project') if key=='P' else None
                    for row in chosen:
                        changes={'project':project or 'Inbox'} if key=='P' else ({'remind_at':remind} if key=='R' else {'status':'done' if key=='C' else 'deleted','remind_at':None})
                        store.change(row['id'],changes,expected=row['revision'])
                    marked.clear(); nudge_sync(); notice='saved'
                elif key in {'\x7f','\b'}: query=query[:-1]; index=0
                elif key=='/': query=prompt('filter'); index=0
                elif len(key)==1 and key.isprintable(): query+=key; index=0
            except (OSError,ValueError,subprocess.CalledProcessError) as exc:
                notice=str(exc)
    finally:
        termios.tcsetattr(fd,termios.TCSADRAIN,old)
        sys.stdout.write('\033[?25h\033[0m\n'); sys.stdout.flush()
    return 0


def main(argv=None,kind=None,read_key=None,hints=None):
    parser=argparse.ArgumentParser(prog='lk notes',description='Offline replicated notebook. Text captures to Inbox; no arguments opens the workspace.')
    parser.add_argument('words',nargs='*')
    parser.add_argument('--project',default='Inbox')
    parser.add_argument('--task',action='store_true')
    parser.add_argument('--remind',metavar='WHEN')
    parser.add_argument('--due',metavar='WHEN')
    parser.add_argument('--target',default='all',help='all or a named node')
    parser.add_argument('--stdin',action='store_true',help='Read multiline note text from standard input')
    parser.add_argument('--json',action='store_true')
    parser.add_argument('--all',action='store_true',help='Include completed records')
    args=parser.parse_intermixed_args(argv)
    store=Notebook()
    try:
        words=args.words
        action=words[0] if words and words[0] in {'list','show','edit','file','done','delete','snooze','resolve','sync','new'} else 'new'
        values=words[1:] if words and words[0]==action else words
        if not words and not args.stdin:
            if sys.stdin.isatty() and sys.stdout.isatty() and read_key and hints:
                return workspace(store,kind,read_key,hints)
            result=store.list(kind=kind,include_done=args.all)
        elif action=='sync': result=daemon('sync',{})
        elif action=='list': result=store.list(' '.join(values),kind,include_done=args.all)
        elif action in {'show','edit'}:
            if len(values)!=1: raise ValueError(action+' requires one note ID')
            matches=[row for row in store.list(include_done=True) if row['id'].startswith(values[0])]
            if len(matches)!=1: raise ValueError('Note ID is missing, ambiguous, or conflicted')
            row=matches[0]
            if action=='edit': edit(store,row); result={'ok':True}
            else:
                if not args.json: print(Path(row['path']).read_text()); return 0
                result=row
        elif action in {'file','done','delete','snooze','resolve'}:
            if not values: raise ValueError(action+' requires a note ID')
            if action=='resolve':
                text=' '.join(values[1:])
                if not text: raise ValueError('resolve requires the reconciled note text')
                result=store.change(values[0],{'title':text.splitlines()[0][:100],'body':text},resolve=True)
            else:
                changes={'project':args.project} if action=='file' else ({'remind_at':timestamp(' '.join(values[1:]) or 'in 10 minutes')} if action=='snooze' else {'status':'done' if action=='done' else 'deleted','remind_at':None})
                result=store.change(values[0],changes)
            nudge_sync()
        else:
            text=sys.stdin.read(MAX_CAPTURE_BYTES) if args.stdin else ' '.join(values)
            if args.stdin and len(text) == MAX_CAPTURE_BYTES: raise ValueError('Note exceeds capture size limit')
            capture_kind='task' if args.task else ('reminder' if args.remind or kind=='reminder' else kind or 'note')
            if capture_kind=='reminder' and not args.remind: raise ValueError('Use --remind WHEN to schedule a reminder')
            result=store.create(text,kind=capture_kind,project=args.project,due=args.due,remind_at=args.remind,target=local_target(args.target))
            nudge_sync()
        if args.json: print(json.dumps(result,ensure_ascii=False,indent=2))
        elif isinstance(result,list):
            for row in result: print(display(row))
        elif 'note' in result: print('SAVED · '+result['note'][:8]+' · '+result['data']['title'])
        else: print(json.dumps(result,ensure_ascii=False))
        return 0
    except (ValueError,OSError,RuntimeError,subprocess.CalledProcessError) as exc:
        print('LOOK NOTEBOOK · '+str(exc),file=sys.stderr); return 1


MAX_CAPTURE_BYTES=256_001


def read_intent(prompt):
    """Resolve bounded notebook observations; no model is needed to list local records."""
    text=' '.join(str(prompt).casefold().strip(' .!?').split())
    if re.fullmatch(r'(?:list|show|read)(?: me)? (?:(?:all|the|our|my|saved) )*(?:notes|notebook|lkn)',text):
        return {'tool':'notebook_list','args':{}}
    if re.fullmatch(r'what (?:do|does) (?:(?:the|our|my|saved) )*(?:notes|notebook|lkn) (?:say|contain|have)',text):
        return {'tool':'notebook_list','args':{}}
    match=re.fullmatch(r'(?:(?:what does|read|show)(?: me)? )?(?:(?:the|our|my) )*(first|second|third|fourth|fifth|last|oldest|newest|\d+)(?:st|nd|rd|th)? note(?: say| contain)?',text)
    if match:
        word=match[1]
        position={'first':1,'second':2,'third':3,'fourth':4,'fifth':5,'newest':1,'last':-1,'oldest':-1}.get(word)
        position=int(word) if position is None else position
        return {'tool':'notebook_read','args':{'position':position}}
    return None


def read_records(store,args):
    identifier=str(args.get('id') or '')
    rows=store.list(include_done=bool(args.get('include_done',False)) or bool(identifier))
    if identifier:
        matches=[row for row in rows if row['id'].startswith(identifier)]
        if len(matches)!=1: raise ValueError('Note ID is missing, ambiguous, or conflicted')
        return matches[0]
    position=args.get('position',1)
    if not isinstance(position,int) or isinstance(position,bool) or position==0:
        raise ValueError('Use a note position starting at 1')
    index=position-1 if position>0 else len(rows)-1
    if not 0<=index<len(rows): raise ValueError('That note position is outside the current notebook list')
    return rows[index]


def direct_read(intent):
    try:
        store=Notebook()
        rows=store.list() if intent['tool']=='notebook_list' else [read_records(store,intent['args'])]
        if not rows: return 'Your notebook has no open notes, tasks, or reminders.'
        answer=['LOOK notebook · current list, newest updated first']
        start=int(intent['args'].get('position') or 1)
        if start<0: start=len(store.list())
        for position,row in enumerate(rows,start):
            answer.extend(['',f"{position}. {row['title']} · {row['project']} · {row['id'][:8]}",row['body']])
        return '\n'.join(answer)
    except (ValueError,OSError) as exc:
        return 'LOOK notebook · '+str(exc)


def tools():
    definitions=[('notebook_search','Search saved notebook records. Omit query or use an empty string to list all records, including completed records. Results include full note bodies.',{'query':{'type':'string'}},[]),
        ('notebook_list','List saved notes, tasks and reminders in current LKN order: most recently updated first. No keyword is required. Results include full bodies.',{'include_done':{'type':'boolean'}},[]),
        ('notebook_read','Read the full text of a saved notebook record by its ID or position in the current LKN list. First note means position 1; positions follow newest updated first.',{'id':{'type':'string'},'position':{'type':'integer','minimum':1},'include_done':{'type':'boolean'}},[]),
        ('notebook_capture','Save a note, task or reminder only when the user asks to record it.',
         {'text':{'type':'string'},'kind':{'type':'string','enum':['note','task','reminder']},'project':{'type':'string'},
          'due':{'type':'string'},'remind_at':{'type':'string'},'target':{'type':'string'}},['text']),
        ('notebook_complete','Complete a saved note/task/reminder explicitly requested by the user.',{'id':{'type':'string'}},['id'])]
    return [{'type':'function','function':{'name':name,'description':description,
        'parameters':{'type':'object','properties':properties,'required':required}}} for name,description,properties,required in definitions]


def tool(name,args):
    store=Notebook()
    if name=='notebook_search': result=store.list(str(args.get('query') or ''),include_done=True)
    elif name=='notebook_list': result=store.list(include_done=bool(args.get('include_done',False)))
    elif name=='notebook_read': result=read_records(store,args)
    elif name=='notebook_capture':
        if args.get('kind')=='reminder' and not args.get('remind_at'): raise ValueError('Reminder needs an explicit date/time')
        options={key:args[key] for key in ('kind','project','due','remind_at') if key in args}
        options['target']=local_target(str(args.get('target') or 'all'))
        result=store.create(args.get('text',''),**options)
        nudge_sync()
    elif name=='notebook_complete': result=store.change(args.get('id',''),{'status':'done','remind_at':None}); nudge_sync()
    else: raise ValueError('Unknown notebook tool')
    return json.dumps(result,ensure_ascii=False)
