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
import unicodedata
import urllib.request
try:
    from . import terminal_style
except ImportError:
    import terminal_style

try:
    from .notebook_core import Notebook, timestamp
    from .notebook_markdown import render as render_markdown, safe_text, extract_links, markdown_link, inline, cell_width, wrap_spans
except ImportError:
    from notebook_core import Notebook, timestamp
    from notebook_markdown import render as render_markdown, safe_text, extract_links, markdown_link, inline, cell_width, wrap_spans


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


SORT_MODES=('updated','created','title','project','due','type')
TYPE_VIEWS=(None,'note','task','reminder')
KEY_CYAN='\033[0;1;38;5;117m'
LABEL_DIM='\033[0;2m'
RESET='\033[0m'


def command_hints(text):
    """Style after wrapping/clipping so ANSI escapes never affect the layout."""
    plain=re.sub(r'\033\[[0-9;]*m','',text)
    colors=terminal_style.list_colors();key='\033[1m'+colors['CYAN'];label=colors['GRAY']
    return '\n'.join(label+re.sub(r'(^\s*| · )(\S+)',
        lambda match:match[1]+key+match[2]+RESET+label,line)+RESET
        for line in plain.split('\n'))



# Keep titles dominant even when a split pane leaves little horizontal room.
NOTE_TYPE_WIDTH=8
NOTE_PROJECT_MAX_WIDTH=20
NOTE_MIN_TITLE_WIDTH=20
NOTE_COLUMN_GAP=2


def column_text(value,width):
    """Clip/pad by terminal cells, preserving Unicode and reserving an ellipsis."""
    text=safe_text(str(value)).replace('\n',' ').replace('\t',' ')
    if sum(map(cell_width,text))<=width:
        return text+' '*(width-sum(map(cell_width,text)))
    shown='';used=0
    for char in text:
        size=cell_width(char)
        if used+size>max(0,width-1):break
        shown+=char;used+=size
    return shown+('…' if width else '')+' '*max(0,width-used-1)


def notebook_columns(width,rows):
    available=max(1,width-4)  # Caret/mark gutter and the terminal's final column.
    project=min(NOTE_PROJECT_MAX_WIDTH,max(7,max((sum(map(cell_width,safe_text(row['project']))) for row in rows),default=7)))
    project=min(project,available//5)
    if available-NOTE_TYPE_WIDTH-project-2*NOTE_COLUMN_GAP>=NOTE_MIN_TITLE_WIDTH:
        return [('title',available-NOTE_TYPE_WIDTH-project-2*NOTE_COLUMN_GAP),('kind',NOTE_TYPE_WIDTH),('project',project)]
    if available-NOTE_TYPE_WIDTH-NOTE_COLUMN_GAP>=NOTE_MIN_TITLE_WIDTH:
        return [('title',available-NOTE_TYPE_WIDTH-NOTE_COLUMN_GAP),('kind',NOTE_TYPE_WIDTH)]
    return [('title',available)]


def notebook_row(row,colors,columns):
    """Aligned columns share one layout across every visible record."""
    roles={'title':'WHITE','kind':{'note':'CYAN','task':'GREEN','reminder':'YELLOW'}[row['kind']],'project':'CYAN'}
    return (' '*NOTE_COLUMN_GAP).join(
        ('\033[1m' if field=='title' else '')+colors[roles[field]]+column_text(row[field],width)+RESET
        for field,width in columns)


def notebook_details(row,colors):
    return (colors['GRAY']+'   '+metadata(row)+' · '+row['id'][:8]+
            (colors['RED']+' · CONFLICT' if row['conflict'] else '')+RESET)


def metadata(row):
    def stamp(value): return dt.datetime.fromtimestamp(value).strftime('%Y-%m-%d %H:%M')
    text='made '+stamp(row['created'])+' · edited '+stamp(row['updated'])
    if row.get('due'): text+=' · due '+stamp(row['due'])
    if row.get('remind_at'): text+=' · remind '+stamp(row['remind_at'])
    return text


def named_records(store,text):
    name=' '.join(text.casefold().split())
    rows=store.list(include_done=True)
    matches=[row for row in rows if ' '.join(row['title'].casefold().split())==name]
    if matches: return matches
    if re.fullmatch(r'[a-f0-9]{8,32}',name): return [row for row in rows if row['id'].startswith(name)]
    return []


HELP_TEXT='''LOOK NOTEBOOK — notes, tasks and reminders share one record.

Capture: N opens a draft. Enter/Ctrl-J inserts a newline; Shift-Enter/Ctrl-S saves.
Escape cancels a draft. Enter opens a boxed Markdown note view.
The view previews headings, bold/italic, lists, checkboxes, quotes and code.
L selects numbered links and command blocks; B shows notes linking back to this ID.
Use a closed ```command fence to make its contents runnable.
Optional header: command label="Project tests" cwd="~/Projects/My Book".
Selecting a command shows its text and local working directory; R confirms execution.
Ordinary code fences stay inert; commands never run during preview or sync.
Y copies this note's complete Markdown link from the list or preview.
Editor Ctrl-K opens Insert Link; Ctrl-T switches to a multiline Command block.
Ctrl-N inside that dialog finds notes by title/project and inserts their ID.
Use [label](note:FULL_ID), [label](<file path>), [label](https://example.com),
or [label](<@3090:/path with spaces>). Relative paths start beside the note.
E shows the original Markdown marks; saving returns to the rendered preview.
In the view: arrows/Space scroll, E edits the body, V opens your full editor.
Quick edits keep the title; Enter adds a newline; Shift-Enter/Ctrl-S saves.
Editor: Option/Alt-Left/Right (or Ctrl-Left/Right) jumps across words.
Option/Alt-Up/Down jumps between blank-line-separated paragraphs.
Shift-Up/Down and Page Up/Down retain page movement.
Shift-Left/Right jumps to the note start/end; Home/End moves within the line.
Escape returns to the list. Explicit lkn edit NAME also opens the full editor.

File (P): change the project label; text and stable ID stay the same.
Done (C): complete the record and stop its reminder. List --all shows it again.
Remind (R): attach a one-time alert to a note or task. Due dates alone are not alerts.
Delete (D): delete after confirmation; a deletion marker syncs to other nodes.

Arrows move; Shift-arrows page/jump; Tab marks; Shift-A selects all shown.
Type filters titles/projects. / toggles full-text search, keeping your query.
Backslash terms subtract matches: project \\old excludes old in the active scope.
Shift-F cycles sort: updated, created, title, project, due/reminder, type.
Shift-T cycles all / notes / tasks / reminders. Rows show made and edited times.
Escape clears the query, then exits. H or ? opens help.

CLI examples:
  lkn Quick thought
  lkn To Do              # first capture, later reopen that exact title
  lkn new To Do          # explicitly create another, even if one exists
  lkn --project LOOK --task Test playback
  lkn --remind "in 10 minutes" Check download
  lkn file NOTE_ID --project LOOK
  lkn done NOTE_ID
  lkn snooze NOTE_ID "in 20 minutes"
  lkn list --all
  lkn sync

Every paired node keeps a local copy. Captures work offline; revisions sync
when peers reconnect. Concurrent edits are preserved as conflicts.
Targets: --target all (default), a node name, or comma-separated node names.
LO can list notes or read a note by its position in the newest-updated-first list.
Reminder durations accept ten minutes, 10 minutes, or in 10 minutes.
Full command flags: lkn --help. Global reference: lk doc or man lk.

Command mode: Tab selects text/label/directory; Enter adds a line in the text.
Shift-Enter/Ctrl-S inserts the block, then save the note as usual.

W opens a sibling shell from the list or note preview, in the current working directory.
Kitty: Option/Alt-Shift-W switches panes; Ctrl-Shift-W closes the focused pane.
tmux uses Ctrl-B then O to switch; exit closes the shell. W stays text in editors.

Editor Ctrl-D starts local dictation; Ctrl-C finishes and inserts at the caret.
Review/edit the transcript before saving. Shift-D remains an ordinary capital D.
Run lk transcribe setup once on this computer before microphone dictation.
'''


def show_help(fd,read_key):
    top=0
    while True:
        width,height=shutil.get_terminal_size((100,30)); page=max(1,height-2)
        rows=[part for line in HELP_TEXT.splitlines() for part in (textwrap.wrap(line,max(1,width-1)) or [''])]
        top=max(0,min(top,max(0,len(rows)-page)))
        footer=command_hints('↑↓ scroll · Space page · Esc/H/? return'[:max(1,width-1)])
        sys.stdout.write('\033[2J\033[H'+'\n'.join(rows[top:top+page])+ '\n'+footer+'\033[J'); sys.stdout.flush()
        key=read_key(fd,None)
        if key in {'esc','H','?','q','\x03'}: return
        if key in {'down','j','\r','\n'}: top+=1
        elif key in {'up','k'}: top-=1
        elif key in {'pagedown',' '}: top+=page
        elif key in {'pageup','b'}: top-=page
        elif key=='home': top=0
        elif key=='end': top=len(rows)


def copy_note_link(row):
    try:
        from .look_renderer import copy_text
    except ImportError:
        from look_renderer import copy_text
    return copy_text(make_link(row['title'],'note:'+row['id']))


def link_target(text):
    """Use existing address forms; creation can bookmark offline paths."""
    from urllib.parse import urlsplit
    text=text.strip()
    if len(text)>1 and text[0]==text[-1] and text[0] in {'"',"'"}: text=text[1:-1]
    if not text or safe_text(text)!=text or any(char in '\n\t<>' for char in text):
        raise ValueError('Use one path, URL, or note link without controls or angle brackets')
    if text.startswith('note:'):
        if not re.fullmatch(r'note:[a-f0-9]{32}',text): raise ValueError('Choose a note with Ctrl-N, or paste its copied link')
    elif text.startswith('@'):
        try:
            from .fabric_files import parse
        except ImportError:
            from fabric_files import parse
        parse(text)
    else:
        parts=urlsplit(text)
        if parts.scheme in {'http','https'}:
            if not parts.hostname: raise ValueError('URL needs a hostname')
        elif parts.scheme=='file':
            if parts.netloc not in {'','localhost'}: raise ValueError('Use @node:/path for a remote file')
        elif parts.scheme: raise ValueError('Use a path, https:// URL, @node:/path, or note link')
    return text


def make_link(label,target):
    target=link_target(target)
    label=' '.join(safe_text(label).split()) or 'Link'
    # A title is a literal label even when it contains Markdown punctuation.
    label=''.join('\\'+char if char in '\\[]*_~'+chr(96) else char for char in label)
    return '['+label+'](<'+target+'>)'


def link_fields(text):
    from urllib.parse import urlsplit,unquote
    text=text.strip(); parsed=markdown_link(text)
    if parsed and parsed[2]==len(text):
        label=''.join(part for part,_ in inline(parsed[0]))
        return link_target(parsed[1]),label
    target=link_target(text)
    parts=urlsplit(target) if not target.startswith('@') else None
    name=(parts.path if parts and parts.scheme in {'http','https','file'} else target).rstrip('/').rsplit('/',1)[-1]
    if parts and parts.scheme in {'http','https'} and not parts.path.strip('/'): name=parts.hostname
    if target.startswith('note:'): name='Note'
    return target,unquote(name) or target


def dialog_line(text,width):
    """Clip untrusted field text in visible terminal cells."""
    output=[]; used=0
    for char in safe_text(text).replace('\n',' ').replace('\t',' '):
        size=cell_width(char)
        if used+size>width: break
        output.append(char); used+=size
    return ''.join(output)


def word_cursor(text,cursor,direction):
    """Move by Unicode word or punctuation group, skipping intervening spaces."""
    def word(char): return char.isalnum() or char=='_' or unicodedata.category(char).startswith('M')
    if direction<0:
        while cursor and text[cursor-1].isspace(): cursor-=1
        if cursor:
            group=word(text[cursor-1])
            while cursor and not text[cursor-1].isspace() and word(text[cursor-1])==group: cursor-=1
    else:
        while cursor<len(text) and text[cursor].isspace(): cursor+=1
        if cursor<len(text):
            group=word(text[cursor])
            while cursor<len(text) and not text[cursor].isspace() and word(text[cursor])==group: cursor+=1
    return cursor


def paragraph_cursor(text,cursor,direction):
    starts=[0]+[match.end() for match in re.finditer(r'\n[ \t]*\n(?:[ \t]*\n)*',text)]
    if direction<0: return next((start for start in reversed(starts) if start<cursor),0)
    return next((start for start in starts if start>cursor),len(text))


def choose_note(store,fd,read_key):
    rows=store.list(include_done=True); query=''; selected=0
    while True:
        terms=query.casefold().split()
        matches=[row for row in rows if not row['conflict'] and
                 all(term in (row['title']+' '+row['project']).casefold() for term in terms)]
        selected=max(0,min(selected,max(0,len(matches)-1)))
        width,height=shutil.get_terminal_size((100,30)); page=max(1,height-4)
        top=max(0,selected-page+1)
        lines=['LINK TO NOTE · type to search','FILTER '+query+'█']
        lines.extend(('› ' if index==selected else '  ')+row['title']+' · '+row['project']
                     for index,row in enumerate(matches[top:top+page],top))
        if not matches: lines.append('No matching notes')
        lines.append('↑↓ select · Enter choose · Esc return')
        sys.stdout.write('\033[2J\033[H'+'\r\n'.join(dialog_line(line,max(1,width-1)) for line in lines)+'\033[J');sys.stdout.flush()
        key=read_key(fd,None)
        if key in {'esc','\x03'}: return None
        if key in {'\r','\n','enter'} and matches: return matches[selected]
        if key=='down': selected+=1
        elif key=='up': selected-=1
        elif key in {'\b','\x7f'}: query=query[:-1];selected=0
        elif key.startswith('paste:'): query+=' '.join(safe_text(key[6:]).split());selected=0
        elif len(key)==1 and key.isprintable(): query+=key;selected=0


def make_command(body,label='',directory=''):
    if not body.strip():raise ValueError('Paste or type a command first')
    validate_command_text(body,directory)
    validate_command_text(label,'')
    if any(unicodedata.category(char) in {'Cc','Cs'} for char in label):
        raise ValueError('Use a single-line label')
    # A longer fence preserves pasted scripts containing literal backticks.
    fence='`'*max(3,1+max((len(run) for run in re.findall(r'`+',body)),default=0))
    header='command'
    if label:header+=' label='+shlex.quote(label)
    if directory:header+=' cwd='+shlex.quote(directory)
    return '\n\n'+fence+header+'\n'+body+'\n'+fence+'\n\n'


def insert_link(store,fd,read_key):
    try:
        from .look_renderer import clipboard_text
    except ImportError:
        from look_renderer import clipboard_text
    clipboard=clipboard_text().replace('\r\n','\n').replace('\r','\n')
    values=['','']; notice=''; active=0; mode='link'
    try:
        values[:]=link_fields(clipboard); active=1
    except ValueError: pass
    cursors=[len(value) for value in values]; replace=[bool(value) for value in values]
    forms={'command':([clipboard,'',''],[len(clipboard),0,0],[bool(clipboard),False,False],0)}
    while True:
        width,height=shutil.get_terminal_size((100,30))
        rows=['INSERT LINK · Type: Link' if mode=='link' else 'INSERT COMMAND · Type: Command']
        names=('Target','Label') if mode=='link' else ('Command','Label','Working directory (optional)')
        for index,(name,value) in enumerate(zip(names,values)):
            cursor=cursors[index]
            shown=value[:cursor]+'█'+value[cursor:] if active==index else value
            if mode=='command' and index==0:
                rows.append(('› ' if active==index else '  ')+name+':')
                body_rows=[part for line in shown.split('\n') for part in
                           (textwrap.wrap(line,max(1,width-5),replace_whitespace=False,drop_whitespace=False) or [''])]
                page=max(1,height-10)
                cursor_row=next((i for i,line in enumerate(body_rows) if '█' in line),0)
                top=max(0,cursor_row-page+1) if active==0 else 0
                rows.extend('    '+line for line in body_rows[top:top+page])
            else:rows.append(('› ' if active==index else '  ')+name+': '+shown)
        rows+=(['Type replaces suggestion · arrows edit · Enter confirms',
                'Tab target/label · Ctrl-N find note · Esc cancel'] if mode=='link' else
               ['Enter newline in Command · Tab next field',
                'Shift-Enter/Ctrl-S insert block · Esc cancel'])
        rows+=['Ctrl-T switch Link / Command',notice]
        sys.stdout.write('\033[2J\033[H'+'\r\n'.join(dialog_line(line,max(1,width-1)) for line in rows)+'\033[J');sys.stdout.flush()
        key=read_key(fd,None);notice=''
        if key in {'esc','\x03'}: return None
        if key=='\x14':
            forms[mode]=(values,cursors,replace,active)
            mode='command' if mode=='link' else 'link'
            values,cursors,replace,active=forms[mode]
            continue
        if key=='\x0e' and mode=='link':
            try:
                row=choose_note(store if store is not None else Notebook(),fd,read_key)
            except (OSError,ValueError) as exc:
                notice=safe_text(str(exc));continue
            if row:
                values=['note:'+row['id'],row['title']];cursors=[len(value) for value in values];replace=[True,True];active=1
            continue
        if key=='\t': active=(active+1)%len(values);continue
        if mode=='command' and (key in {'shiftenter','\x13'} or (key in {'\r','\n','enter'} and active==2)):
            try:return make_command(*values)
            except ValueError as exc:notice=str(exc)
            continue
        if mode=='command' and key in {'\r','\n','enter'}:
            if active==0:
                replace[0]=False
                cursor=cursors[0];values[0]=values[0][:cursor]+'\n'+values[0][cursor:];cursors[0]+=1
            else:active=2
            continue
        if key in {'\r','\n','enter'}:
            try:
                if active==0:
                    target,label=link_fields(values[0]);values[0]=target
                    if not values[1] or replace[1]: values[1]=label;replace[1]=True
                    cursors=[len(value) for value in values];active=1
                else: return make_link(values[1],values[0])
            except ValueError as exc: notice=str(exc);active=0
            continue
        if mode=='command' and active==0 and key in {'up','down'}:
            replace[0]=False;text=values[0];cursor=cursors[0]
            start=text.rfind('\n',0,cursor)+1;column=cursor-start;end=text.find('\n',cursor)
            if key=='up' and start:
                previous=text.rfind('\n',0,start-1)+1;cursors[0]=min(previous+column,start-1)
            elif key=='down' and end>=0:
                following=text.find('\n',end+1);cursors[0]=min(end+1+column,len(text) if following<0 else following)
            continue
        if key in {'wordleft','wordright','left','right','home','end'}:
            replace[active]=False
            if key in {'wordleft','wordright'}:
                cursors[active]=word_cursor(values[active],cursors[active],-1 if key=='wordleft' else 1)
            elif key=='left': cursors[active]=max(0,cursors[active]-1)
            elif key=='right': cursors[active]=min(len(values[active]),cursors[active]+1)
            elif key=='home': cursors[active]=values[active].rfind('\n',0,cursors[active])+1 if mode=='command' and active==0 else 0
            else:
                end=values[active].find('\n',cursors[active]) if mode=='command' and active==0 else -1
                cursors[active]=len(values[active]) if end<0 else end
            continue
        if key in {'\b','\x7f','delete'}:
            value=values[active];cursor=cursors[active]
            if replace[active]: value='';cursor=0
            elif key=='delete': value=value[:cursor]+value[cursor+1:]
            elif cursor: value=value[:cursor-1]+value[cursor:];cursor-=1
            values[active]=value;cursors[active]=cursor;replace[active]=False;continue
        text=key[6:] if key.startswith('paste:') else key if len(key)==1 and key.isprintable() else ''
        if text:
            # Paste is field data, never dialog keys.
            if mode=='command' and active==0:
                text=text.replace('\r\n','\n').replace('\r','\n')
                try:validate_command_text(text,'')
                except ValueError as exc:notice=str(exc);continue
            elif any(ord(char)<32 or ord(char)==127 for char in text):
                notice='Paste a single target or label';continue
            if replace[active]: values[active]='';cursors[active]=0;replace[active]=False
            cursor=cursors[active];values[active]=values[active][:cursor]+text+values[active][cursor:];cursors[active]+=len(text)


def insert_dictation(text,cursor,spoken):
    """Insert speech as editable text, separating adjacent words at the caret."""
    spoken=safe_text(spoken).strip()
    if not spoken:return text,cursor
    punctuation=',.;:!?)]}'
    if cursor and not text[cursor-1].isspace() and spoken[0] not in punctuation:spoken=' '+spoken
    if cursor<len(text) and not text[cursor].isspace() and text[cursor] not in punctuation:spoken+=' '
    return text[:cursor]+spoken+text[cursor:],cursor+len(spoken)


def dictate_for_editor(fd,previous):
    """Temporarily leave raw editor input so Ctrl-C finishes speech, not the draft."""
    try:
        from . import transcription
    except ImportError:
        import transcription
    sys.stdout.write('\033[?2004l\033[<u\033[2J\033[HNOTE DICTATION · Ctrl-C finishes and returns text to your draft\n')
    sys.stdout.flush()
    termios.tcsetattr(fd,termios.TCSADRAIN,previous)
    try:return transcription.dictate()
    finally:
        tty.setraw(fd)
        sys.stdout.write('\033[>1u\033[?2004h');sys.stdout.flush()


def capture_note(fd,read_key,initial_text='',label='NEW NOTE',store=None):
    """Paste and ordinary Enter never submit a draft."""
    previous=termios.tcgetattr(fd)
    text=safe_text(initial_text); cursor=len(text); notice=''
    try:
        tty.setraw(fd)
        sys.stdout.write('\033[>1u\033[?2004h')
        while True:
            width,height=shutil.get_terminal_size((100,30))
            boxed=label!='NEW NOTE'; columns=max(1,min(96,width-4)) if boxed else max(1,width-1)
            before=text[:cursor]; after=text[cursor:]
            rows=(before+'█'+after).split('\n')
            rows=[part for line in rows for part in (textwrap.wrap(line,columns,replace_whitespace=False,drop_whitespace=False) or [''])]
            cursor_row=next((index for index,line in enumerate(rows) if '█' in line),0)
            notice_rows=textwrap.wrap(safe_text(notice),max(1,width-1))[:3] if notice else []
            page=max(1,height-((6 if boxed else 4)+len(notice_rows)))
            top=max(0,cursor_row-page+1)
            visible=rows[top:top+page]
            heading=(label+' · ')[:max(1,width-1)]
            actions='Enter newline · Shift-Enter/Ctrl-S save · Esc cancel'[:max(0,width-1-len(heading))]
            frame=[KEY_CYAN+heading+'\033[0m'+command_hints(actions),
                   command_hints('Ctrl-D dictate · Ctrl-K insert link/command · Alt-arrows words/paragraphs'[:max(1,width-1)]),
                   *notice_rows]
            if boxed:
                frame.extend(['┌'+'─'*columns+'┐',*['│'+line.ljust(columns)+'│' for line in visible],'└'+'─'*columns+'┘'])
            else: frame.extend(visible)
            sys.stdout.write('\033[2J\033[H'+'\r\n'.join(frame)+'\033[J'); sys.stdout.flush()
            key=read_key(fd,None)
            if key in {'esc','\x03'}: return None
            if key in {'shiftenter','\x13'}: return text
            if key=='\x04':
                try:
                    spoken=dictate_for_editor(fd,previous)
                    text,cursor=insert_dictation(text,cursor,spoken)
                    notice='Dictation inserted · edit freely · Ctrl-S saves' if spoken.strip() else 'No speech inserted · draft unchanged'
                except KeyboardInterrupt:notice='Dictation cancelled · draft unchanged'
                except (OSError,ValueError,RuntimeError,subprocess.SubprocessError) as exc:notice='Dictation: '+str(exc)
                continue
            if key=='\x0b':
                linked=insert_link(store,fd,read_key)
                if linked: text=text[:cursor]+linked+text[cursor:];cursor+=len(linked)
                continue
            if key.startswith('paste:'):
                pasted=safe_text(key[6:]); text=text[:cursor]+pasted+text[cursor:]; cursor+=len(pasted)
                continue
            if key in {'\r','enter','\n'}:
                text=text[:cursor]+'\n'+text[cursor:]; cursor+=1
            elif key in {'\x7f','\b'} and cursor:
                text=text[:cursor-1]+text[cursor:]; cursor-=1
            elif key=='left': cursor=max(0,cursor-1)
            elif key=='right': cursor=min(len(text),cursor+1)
            elif key in {'wordleft','wordright'}: cursor=word_cursor(text,cursor,-1 if key=='wordleft' else 1)
            elif key in {'paragraphup','paragraphdown'}: cursor=paragraph_cursor(text,cursor,-1 if key=='paragraphup' else 1)
            elif key=='delete': text=text[:cursor]+text[cursor+1:]
            elif key=='shiftleft': cursor=0
            elif key=='shiftright': cursor=len(text)
            elif key in {'up','down','pageup','pagedown','shiftup','shiftdown'}:
                start=text.rfind('\n',0,cursor)+1; column=cursor-start
                count=1 if key in {'up','down'} else page
                for _ in range(count):
                    start=text.rfind('\n',0,cursor)+1; end=text.find('\n',cursor)
                    if key in {'up','pageup','shiftup'} and start:
                        prior=text.rfind('\n',0,start-1)+1
                        cursor=min(prior+column,start-1)
                    elif key in {'down','pagedown','shiftdown'} and end>=0:
                        following=text.find('\n',end+1)
                        cursor=min(end+1+column,len(text) if following<0 else following)
                    else: break
            elif key=='home': cursor=text.rfind('\n',0,cursor)+1
            elif key=='end':
                next_line=text.find('\n',cursor); cursor=len(text) if next_line<0 else next_line
            elif len(key)==1 and key.isprintable():
                text=text[:cursor]+key+text[cursor:]; cursor+=1
    finally:
        sys.stdout.write('\033[?2004l\033[<u'); sys.stdout.flush()
        termios.tcsetattr(fd,termios.TCSADRAIN,previous)


def quick_edit(store,row,fd,read_key):
    draft=capture_note(fd,read_key,row['body'],'EDIT · '+safe_text(row['title']),store=store)
    if draft is None or draft==row['body']: return ''
    try:
        store.change(row['id'],{'body':draft},expected=row['revision'])
    except (ValueError,OSError):
        # A peer may have edited while this draft was open. Preserve both texts.
        directory=store.root/'drafts'; directory.mkdir(parents=True,exist_ok=True)
        path=directory/(row['id']+'-'+str(time.time_ns())+'.md')
        path.write_text(draft,encoding='utf-8')
        return 'Note changed or save failed; draft preserved at '+str(path)
    nudge_sync()
    return 'saved'



def validate_command_text(command,directory):
    for text in (command,directory):
        if any((unicodedata.category(char) in {'Cc','Cs'} and char not in '\n\t') or
               char in '\u202a\u202b\u202c\u202d\u202e\u2066\u2067\u2068\u2069' for char in text):
            raise ValueError('Command contains hidden or terminal controls')
    if '\n' in directory or '\t' in directory or directory.startswith('@'):
        raise ValueError('Commands need a local working directory')


def resolve_command(row,target):
    command=target.get('command');directory=target.get('cwd','')
    if not isinstance(command,str) or not command.strip() or not isinstance(directory,str):
        raise ValueError('Command block needs command text and a local working directory')
    validate_command_text(command,directory)
    cwd=Path(directory).expanduser() if directory else Path.cwd()
    if directory and not cwd.is_absolute():cwd=Path(row['path']).parent/cwd
    cwd=cwd.resolve()
    if not cwd.is_dir():raise ValueError('Command working directory does not exist')
    return {'command':command,'cwd':cwd}


def confirm_command(fd,read_key,target):
    """Require a deliberate run key after showing the exact source and cwd."""
    top=0
    while True:
        width,height=shutil.get_terminal_size((100,30));width=max(1,width-1);page=max(1,height-3)
        lines=[]
        for line in ('Working directory: '+str(target['cwd'])+'\n\n'+target['command']).split('\n'):
            lines.extend(wrap_spans([(safe_text(line).expandtabs(4),())],width))
        top=max(0,min(top,max(0,len(lines)-page)))
        frame=['RUN NOTE COMMAND'[:width]]+lines[top:top+page]+['↑↓/Space scroll · R run · Esc cancel'[:width]]
        sys.stdout.write('\033[2J\033[H'+'\n'.join(frame)+'\033[J');sys.stdout.flush()
        key=read_key(fd,None)
        if key in {'R','r'}:return True
        if key in {'esc','q','\x03'}:return False
        if key in {'down','j'}:top+=1
        elif key in {'up','k'}:top-=1
        elif key in {'pagedown',' '}:top+=page
        elif key=='pageup':top-=page


def run_note_command(target):
    shell=os.environ.get('SHELL') or '/bin/sh'
    sys.stdout.write('\033[2J\033[H'+safe_text('Working directory: '+str(target['cwd'])+'\n'+target['command'])+'\n\n')
    sys.stdout.flush()
    try:
        code=subprocess.run([shell,'-c',target['command']],cwd=target['cwd'],check=False).returncode
    except KeyboardInterrupt:code=130
    try:input(f'\nCommand exited {code}. Press Enter to return to the note. ')
    except (KeyboardInterrupt,EOFError):pass
    return code


def resolve_link(store,row,target):
    """Validate targets; only explicit command blocks may request execution."""
    if isinstance(target,dict):
        if target.get('kind')!='command':raise ValueError('Unknown note action')
        return 'command',resolve_command(row,target)
    from urllib.parse import urlsplit, unquote
    try:
        from . import fabric_files
    except ImportError:
        import fabric_files
    if any(ord(char)<32 or ord(char)==127 for char in target) or '\\x1b' in target:
        raise ValueError('Link contains terminal controls')
    if target.startswith('note:'):
        identity=target[5:]
        if not re.fullmatch(r'[a-f0-9]{32}',identity): raise ValueError('Note links need the full stable ID')
        matches=[item for item in store.list(include_done=True) if item['id']==identity]
        if not matches: raise ValueError('Linked note is missing or deleted')
        if len(matches)!=1: raise ValueError('Linked note has a conflict; resolve it from the list')
        return 'note',matches[0]
    if target.startswith('@'):
        return 'fabric',fabric_files.parse(target)
    parsed=urlsplit(target)
    if parsed.scheme in {'http','https'}:
        if not parsed.hostname: raise ValueError('URL needs a hostname')
        return 'url',target
    if parsed.scheme=='file':
        if parsed.netloc not in {'','localhost'}: raise ValueError('Use @node:/path for remote files')
        target=unquote(parsed.path)
    elif parsed.scheme:
        raise ValueError('Supported links: http(s), file, note:ID, and @node:/path')
    path=Path(target).expanduser()
    if not path.is_absolute(): path=Path(row['path']).parent/path
    path=path.resolve()
    if not path.exists(): raise ValueError('Linked path does not exist')
    return 'path',path


def related_notes(store,row):
    target='note:'+row['id']
    return [(item['title'],'note:'+item['id'])
            for item in store.list(include_done=True)
            if item['id']!=row['id'] and any(link==target for _,link in extract_links(item['body']))]


def choose_link(fd,read_key,links,label='NOTE LINKS'):
    selected=0; digits=''
    while links:
        width,height=shutil.get_terminal_size((100,30)); page=max(1,height-4)
        top=max(0,selected-page+1)
        lines=[label]
        lines.extend(('› ' if i==selected else '  ')+str(i+1)+'. '+safe_text(name)+' · '+safe_text(target['command'].replace('\n',' · ') if isinstance(target,dict) else target)
                     for i,(name,target) in enumerate(links[top:top+page],top))
        lines.append('↑↓/Tab select · number then Enter open · Esc back '+digits)
        sys.stdout.write('\033[2J\033[H'+'\n'.join(line[:max(1,width-1)] for line in lines)+'\033[J'); sys.stdout.flush()
        key=read_key(fd,None)
        if key in {'esc','q','\x03'}: return None
        if key in {'down','\t'}: selected=(selected+1)%len(links); digits=''
        elif key=='up': selected=(selected-1)%len(links); digits=''
        elif key in {'\r','\n','enter'}:
            index=int(digits)-1 if digits else selected
            if 0<=index<len(links): return links[index][1]
            digits=''
        elif key in '0123456789' and len(key)==1: digits=(digits+key)[-6:]
        elif key in {'\b','\x7f'}: digits=digits[:-1]
    return None


def open_link(kind,target):
    if kind=='fabric':
        try:
            from .look_renderer import browse_fabric
        except ImportError:
            from look_renderer import browse_fabric
        browse_fabric(target)
        return
    if kind=='path':
        args=[sys.executable,str(Path(__file__).with_name('look_renderer.py')),
              str(target if target.is_dir() else target.parent),'--interactive','--select',str(target)]
    else:
        args=['open' if sys.platform=='darwin' else 'xdg-open',str(target)]
    subprocess.run(args,check=True)

def note_view(store,row,read_key):
    """Own terminal state so the same view works from the list and named CLI entry."""
    fd=sys.stdin.fileno(); old=termios.tcgetattr(fd); top=0; notice=''; pane_help=False
    try:
        tty.setcbreak(fd); sys.stdout.write('\033[?25l')
        while True:
            width,height=shutil.get_terminal_size((100,30))
            controls='↑↓/Space scroll · W shell pane · L links · Y copy link · B related · E edit · V editor · H help · Esc back'
            if pane_help:controls+=' · '+' · '.join(terminal_style.pane_shortcuts())
            control_rows=textwrap.wrap(controls,max(1,width-1))
            inner=max(1,min(96,width-4)); page=max(1,height-5-len(control_rows))
            links=[]
            content=render_markdown(row['body'],inner,links)
            top=max(0,min(top,max(0,len(content)-page)))
            border='─'*inner
            title_rows=render_markdown(row['title'],max(1,width-1))
            title=re.sub(r'\033\[[0-9;]*m','',title_rows[0]).rstrip() if title_rows else ''
            frame=[KEY_CYAN+title+RESET,
                   '\033[0;2m'+metadata(row)[:max(1,width-1)]+'\033[0m','┌'+border+'┐']
            for line in content[top:top+page]:
                frame.append('│'+line+'│')
            frame.extend(['│'+' '*inner+'│']*max(0,page-len(content[top:top+page])))
            frame.extend(['└'+border+'┘',command_hints('\n'.join(control_rows)),notice[:max(1,width-1)]])
            sys.stdout.write('\033[2J\033[H'+'\n'.join(frame)+'\033[J'); sys.stdout.flush()
            key=read_key(fd,1)
            if not key:continue
            if key in {'esc','q','\x03'}: return
            if key in {'down','j','\r','\n'}: top+=1
            elif key in {'up','k'}: top-=1
            elif key in {'pagedown','shiftdown',' '}: top+=page
            elif key in {'pageup','shiftup'}: top-=page
            elif key in {'home','shiftleft'}: top=0
            elif key in {'end','shiftright'}: top=len(content)
            elif key=='W':
                notice=terminal_style.open_pane(Path.cwd())
                if notice.startswith('Shell opened beside LOOK'):pane_help=True
            elif key in {'H','?'}: show_help(fd,read_key)
            elif key=='Y':
                notice='Copied note link · paste into another note' if copy_note_link(row) else 'Clipboard unavailable'
            elif key in {'L','B'} or (len(key)==1 and key in '123456789' and int(key)<=len(links)):
                options=links if key!='B' else related_notes(store,row)
                target=links[int(key)-1][1] if key in '123456789' else choose_link(fd,read_key,options,'NOTE LINKS' if key=='L' else 'RELATED NOTES')
                if target is None:
                    notice='' if options else 'No links' if key=='L' else 'No related notes'
                    continue
                try:
                    kind,value=resolve_link(store,row,target)
                    if kind=='note':
                        row=value; top=0; notice=''
                    else:
                        if kind=='command' and not confirm_command(fd,read_key,value):
                            notice='Command cancelled';continue
                        termios.tcsetattr(fd,termios.TCSADRAIN,old)
                        sys.stdout.write('\033[?25h'); sys.stdout.flush()
                        try:
                            code=run_note_command(value) if kind=='command' else open_link(kind,value)
                        finally:
                            tty.setcbreak(fd); sys.stdout.write('\033[?25l')
                        notice=('Command exited '+str(code)) if kind=='command' else 'Opened '+safe_text(target)
                except (ValueError,OSError,RuntimeError,subprocess.SubprocessError) as exc:
                    notice=safe_text(str(exc))
            elif key in {'E','V'}:
                if key=='E':
                    notice='Resolve this conflict in the full editor (V).' if row['conflict'] else quick_edit(store,row,fd,read_key)
                else:
                    termios.tcsetattr(fd,termios.TCSADRAIN,old)
                    sys.stdout.write('\033[?25h'); sys.stdout.flush()
                    try: edit(store,row)
                    finally:
                        tty.setcbreak(fd); sys.stdout.write('\033[?25l')
                matches=[item for item in store.list(include_done=True) if item['id']==row['id']]
                row=next((item for item in matches if item['revision']==row['revision']),matches[0] if matches else row)
    finally:
        termios.tcsetattr(fd,termios.TCSADRAIN,old)
        sys.stdout.write('\033[?25h\033[0m'); sys.stdout.flush()


def workspace(store,kind,read_key,hints,initial_query=''):
    fd=sys.stdin.fileno(); old=termios.tcgetattr(fd)
    query=initial_query; index=0; marked=set(); notice=''; scope='title'; sort='updated'; focused=None; pane_help=False
    colors=terminal_style.list_colors()
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
            rows=store.list(query,kind,scope=scope,sort=sort)
            if focused:
                index=next((i for i,row in enumerate(rows) if row['revision']==focused),index)
                focused=None
            index=max(0,min(index,max(0,len(rows)-1)))
            width,height=shutil.get_terminal_size((100,30))
            controls='↑↓ move · W shell pane · Tab mark · Enter view · V full editor · Y copy link · N new · P file · C done · D delete · R remind · F sort · T type · / full text · H help · Esc clear/exit'
            if pane_help:controls+=' · '+' · '.join(terminal_style.pane_shortcuts())
            control_rows=hints(controls,width).splitlines()
            usable=max(1,(height-5-len(control_rows))//2)
            top=max(0,index-usable+1)
            columns=notebook_columns(width,rows)
            headings=' '*NOTE_COLUMN_GAP
            headings=headings.join(column_text({'title':'Title','kind':'Type','project':'Project'}[field],size) for field,size in columns)
            lines=[KEY_CYAN+'LOOK NOTEBOOK'+RESET+' · '+(kind or 'all')+f' · sort {sort} · {len(rows)} shown · {len(marked)} marked',colors['GRAY']+'   '+headings+RESET]
            for number,row in enumerate(rows[top:top+usable],top):
                marker='✓' if row['id'] in marked else ' '
                selected=number==index
                line=colors['YELLOW']+('›' if selected else ' ')+marker+' '+notebook_row(row,colors,columns)
                lines.append(terminal_style.list_row(line,width,number,selected,colors))
                lines.append(terminal_style.list_row(notebook_details(row,colors),width,number,selected,colors))
            while len(lines)<height-2-len(control_rows): lines.append('')
            lines.extend([('FILTER ' if scope=='title' else 'SEARCH ')+query+'█',command_hints('\n'.join(control_rows)),notice])
            sys.stdout.write('\033[H'+ '\033[K\n'.join(lines)+'\033[K\033[J'); sys.stdout.flush()
            key=read_key(fd,1)
            if not key: continue
            notice=''; chosen=[row for row in rows if row['id'] in marked] or rows[index:index+1]
            if key=='\x03' or (key=='q' and not query): break
            if key=='esc':
                if query: query=''; index=0; continue
                break
            if key=='W':
                notice=terminal_style.open_pane(Path.cwd())
                if notice.startswith('Shell opened beside LOOK'):pane_help=True
                continue
            if key in {'H','?'}:
                show_help(fd,read_key); continue
            if key=='F':
                focused=rows[index]['revision'] if rows else None
                sort=SORT_MODES[(SORT_MODES.index(sort)+1)%len(SORT_MODES)]; continue
            if key=='T':
                kind=TYPE_VIEWS[(TYPE_VIEWS.index(kind)+1)%len(TYPE_VIEWS)]; index=0; continue
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
                    try: note_view(store,rows[index],read_key)
                    finally:
                        tty.setcbreak(fd); sys.stdout.write('\033[?25l')
                elif key=='Y' and rows:
                    notice='Copied note link · paste into another note' if copy_note_link(rows[index]) else 'Clipboard unavailable'
                elif key=='V' and rows:
                    termios.tcsetattr(fd,termios.TCSADRAIN,old)
                    try: edit(store,rows[index])
                    finally: tty.setcbreak(fd)
                elif key=='N':
                    text=capture_note(fd,read_key,store=store)
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
                elif key=='/': scope='all' if scope=='title' else 'title'; index=0
                elif len(key)==1 and key.isprintable(): query+=key; index=0
            except (OSError,ValueError,subprocess.CalledProcessError) as exc:
                notice=str(exc)
    finally:
        termios.tcsetattr(fd,termios.TCSADRAIN,old)
        sys.stdout.write('\033[?25h\033[0m\n'); sys.stdout.flush()
    return 0


def main(argv=None,kind=None,read_key=None,hints=None):
    parser=argparse.ArgumentParser(prog='lk notes',description='Offline replicated notebook. Text captures to Inbox; no arguments opens the workspace.',epilog=HELP_TEXT,formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('words',nargs='*')
    parser.add_argument('--project',default='Inbox',help='Project label for capture or file; defaults to Inbox')
    parser.add_argument('--task',action='store_true',help='Capture a task instead of a note')
    parser.add_argument('--remind',metavar='WHEN',help='Schedule a one-time reminder, e.g. "Saturday 9am"')
    parser.add_argument('--due',metavar='WHEN',help='Task due date; does not create an alert')
    parser.add_argument('--target',default='all',help='all or a named node')
    parser.add_argument('--stdin',action='store_true',help='Read multiline note text from standard input')
    parser.add_argument('--json',action='store_true',help='Print structured JSON instead of human output')
    parser.add_argument('--all',action='store_true',help='Include completed records')
    if argv==['help']: argv=['--help']
    args=parser.parse_intermixed_args(argv)
    store=Notebook()
    try:
        words=args.words
        action=words[0] if words and words[0] in {'list','show','edit','file','done','delete','snooze','resolve','sync','new'} else 'new'
        explicit=bool(words and words[0] in {'list','show','edit','file','done','delete','snooze','resolve','sync','new'})
        values=words[1:] if words and words[0]==action else words
        structured=args.task or args.remind or args.due or args.stdin or args.project!='Inbox' or args.target!='all' or kind is not None
        if words and not explicit and not structured:
            matches=named_records(store,' '.join(words))
            if len(matches)==1 and not matches[0]['conflict']:
                row=matches[0]
                if args.json: print(json.dumps(row,ensure_ascii=False,indent=2))
                elif sys.stdin.isatty() and sys.stdout.isatty() and read_key: note_view(store,row,read_key)
                else: print(Path(row['path']).read_text())
                return 0
            if matches:
                if sys.stdin.isatty() and sys.stdout.isatty() and read_key and hints:
                    return workspace(store,None,read_key,hints,initial_query=' '.join(words))
                raise ValueError('Multiple or conflicting notes match that name; use a note ID to choose')
        if not words and not args.stdin:
            if sys.stdin.isatty() and sys.stdout.isatty() and read_key and hints:
                return workspace(store,kind,read_key,hints)
            result=store.list(kind=kind,include_done=args.all)
        elif action=='sync': result=daemon('sync',{})
        elif action=='list': result=store.list(' '.join(values),kind,include_done=args.all)
        elif action in {'show','edit'}:
            if not values: raise ValueError(action+' requires a note name or ID')
            matches=named_records(store,' '.join(values))
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
        answer=['LOOK notebook · default list, newest updated first']
        start=int(intent['args'].get('position') or 1)
        if start<0: start=len(store.list())
        for position,row in enumerate(rows,start):
            answer.extend(['',f"{position}. {row['title']} · {row['project']} · {row['id'][:8]}",row['body']])
        return '\n'.join(answer)
    except (ValueError,OSError) as exc:
        return 'LOOK notebook · '+str(exc)


def tools():
    definitions=[('notebook_search','Search saved notebook records. Omit query or use an empty string to list all records, including completed records. Results include full note bodies.',{'query':{'type':'string'}},[]),
        ('notebook_list','List saved notes, tasks and reminders in default LKN order: most recently updated first. No keyword is required. Results include full bodies.',{'include_done':{'type':'boolean'}},[]),
        ('notebook_read','Read the full text of a saved notebook record by its ID or position in the default LKN list. First note means position 1; positions follow newest updated first.',{'id':{'type':'string'},'position':{'type':'integer','minimum':1},'include_done':{'type':'boolean'}},[]),
        ('notebook_capture','Save a note, task or reminder only when the user asks to record it.',
         {'text':{'type':'string'},'kind':{'type':'string','enum':['note','task','reminder']},'project':{'type':'string'},
          'due':{'type':'string'},'remind_at':{'type':'string'},'target':{'type':'string'}},['text']),
        ('notebook_complete','Complete a saved note/task/reminder explicitly requested by the user.',{'id':{'type':'string'}},['id']),
        ('notebook_update','Edit or append to an existing note/task/reminder only when requested. Read it first; use its id and revision. Change remind_at to reschedule, or null to remove an alert. Preserve unspecified fields.',
         {'id':{'type':'string'},'revision':{'type':'string'},'append_text':{'type':'string'},
          'changes':{'type':'object','additionalProperties':False,'properties':{
              'title':{'type':'string'},'body':{'type':'string'},'project':{'type':'string'},
              'kind':{'type':'string','enum':['note','task','reminder']},
              'status':{'type':'string','enum':['open','done']},
              'due':{'type':['string','null']},'remind_at':{'type':['string','null']},'target':{'type':'string'}}}},['id','revision'])]
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
    elif name=='notebook_update':
        if not args.get('revision'): raise ValueError('Read the record first; its revision is required')
        row=read_records(store,{'id':args.get('id',''),'include_done':True})
        changes=dict(args.get('changes') or {})
        allowed={'title','body','project','kind','status','due','remind_at','target'}
        if set(changes)-allowed: raise ValueError('Unknown notebook update field')
        if changes.get('status')=='deleted': raise ValueError('Deletion is not an editing action')
        if 'append_text' in args:
            if 'body' in changes: raise ValueError('Use append_text or body, not both')
            if not isinstance(args['append_text'],str): raise ValueError('Append text must be a string')
            changes['body']=row['body']+('\n' if row['body'] and not row['body'].endswith('\n') else '')+args['append_text']
        if not changes: raise ValueError('No changes supplied')
        for field in ('due','remind_at'):
            if field in changes: changes[field]=timestamp(changes[field])
        if 'target' in changes: changes['target']=local_target(changes['target'])
        if changes.get('status')=='done': changes['remind_at']=None
        if changes.get('kind',row['kind'])=='reminder' and changes.get('status',row['status'])=='open' and not changes.get('remind_at',row['remind_at']):
            raise ValueError('An open reminder needs a date/time')
        result=store.change(row['id'],changes,expected=args['revision']); nudge_sync()
    else: raise ValueError('Unknown notebook tool')
    return json.dumps(result,ensure_ascii=False)
