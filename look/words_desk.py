"""Persistent word desk: editable input, source-backed results and terminal panes."""
from pathlib import Path
import re
import sys
import termios
import tty
import clipboard_shelf
import terminal_style
from media_ui_work import LatestWork
from notebook_markdown import safe_text,cell_width
import words

VIEWS=('Meaning','Synonyms','Antonyms','Spelling','Patterns')
ACTIONS=('lookup','lookup','lookup','spell','find')


def entries(value,view):
    """Turn reference results into readable rows with explicit copy/open actions."""
    if not value:return [{'title':'Reference unavailable','detail':'Try again or inspect lk words status.'}]
    if value.get('loading'):return [{'title':'Looking up local reference…','detail':'You can keep typing or press Esc.'}]
    if value.get('error'):return [{'title':'Reference unavailable','detail':value['error']}]
    if 'results' in value:
        rows=[]
        for sense in value['results']:
            meaning='; '.join(sense['definitions'])
            if view in (1,2):
                field='synonyms' if view==1 else 'antonyms'
                rows += [{'title':word,'detail':field[:-1].title()+' · '+meaning+' · '+sense['part_of_speech'],'target':word,'copy':word} for word in sense[field]]
                if view==1:
                    rows += [{'title':word,'detail':'Related (similar), not a direct synonym · '+meaning,'target':word,'copy':word} for word in sense.get('related',{}).get('similar',[]) if word not in sense[field]]
            else:
                detail=[meaning,*['Example: '+words.example_text(v) for v in sense['examples']]]
                for field in ('synonyms','antonyms'):
                    if sense[field]:detail.append(field.title()+': '+', '.join(sense[field]))
                for field,labels in sense.get('related',{}).items():detail.append({'hypernym':'Broader','hyponym':'More specific','similar':'Similar'}[field]+': '+', '.join(labels))
                rows.append({'title':sense['lemma']+' · '+sense['part_of_speech'],'detail':'\n'.join(detail),'copy':sense['lemma']+'\n'+'\n'.join(detail)})
        if value.get('system_text'):rows.append({'title':'System WordNet','detail':value['system_text'],'copy':value['system_text']})
        return rows or [{'title':'No '+('synonyms' if view==1 else 'antonyms' if view==2 else 'entry')+' recorded for this word',
                         'detail':value.get('hint') or 'Try Meaning for definitions and other related senses. This reference does not list every possible alternative.'}]
    if 'words' in value:
        rows=[]
        for item in value['words']:
            if item['recognized'] is True:continue
            label='check spelling' if item['recognized'] is False else 'not in available vocabulary'
            rows.append({'title':item['word']+' · '+label,'detail':item['source'],'issue':item['word'],'copy':item['word']})
            rows += [{'title':'→ '+suggestion,'detail':'Enter replaces “'+item['word']+'” in the working text',
                      'issue':item['word'],'replacement':suggestion,'copy':suggestion} for suggestion in item['suggestions']]
        return rows or [{'title':'No words flagged','detail':'All checked words are recognized. This checks spelling, not grammar.'}]
    if 'matches' in value:
        return [{'title':word,'detail':value.get('source') or 'Local word list','target':word,'copy':word} for word in value['matches']] or [{'title':'No matching words','detail':'Use * for any letters and ? for one letter, for example ?ight.'}]
    return [{'title':'Offline reference ready' if value.get('installed') else 'Install the portable word reference',
             'detail':('Type a word, paste text, or choose a view. System tools remain available.' if value.get('installed') else 'Esc then S opens setup · about 12 MB to download, roughly 60 MB installed. System tools can still work without this download.')}]


def replace_word(text,old,new):
    return re.sub(r'(?<!\w)'+re.escape(old)+r'(?!\w)',lambda match:new,text)


def copy(text):
    copied=clipboard_shelf.copy_clipboard(text)
    shelf=clipboard_shelf.Shelf()
    try:shelf.observe(text)
    finally:shelf.close()
    return 'Copied to clipboard and LK Clip' if copied else 'Saved to LK Clip · system clipboard unavailable'


def input_line(text,cursor,width):
    """Keep the insertion point visible using terminal cells, including Unicode."""
    before=safe_text(text[:cursor]).replace('\n','↵').replace('\t',' ')
    after=safe_text(text[cursor:]).replace('\n','↵').replace('\t',' ')
    budget=max(1,width-3);prefix=[];used=0
    for char in reversed(before):
        size=cell_width(char)
        if used+size>budget//2:break
        prefix.append(char);used+=size
    return ('…' if len(prefix)<len(before) else '')+''.join(reversed(prefix))+'▏'+after


def desk(ui,*,node=None,language='en_US',initial='',view=0):
    if not sys.stdin.isatty() or not sys.stdout.isatty():raise ValueError('Use lk words lookup WORD or lk words status --json outside a terminal')
    fd=sys.stdin.fileno();old=termios.tcgetattr(fd)
    work=LatestWork();text=initial;cursor=len(text);committed=text;editing=not bool(initial)
    view=max(0,min(len(VIEWS)-1,view));selected=0;top=0;notice='Type a word or paste text · / edits the current query'
    operation=ACTIONS[view] if text else 'status';revision=0;last=None;help_visible=False;pane_help=False
    request_key=None;value={'loading':True};history=[];welcome=not bool(initial)
    def run(action,query):
        try:
            if node:
                import fabric_files,json
                return fabric_files.request('/v1/words',{'target':node},json.dumps({'action':action,'query':query,'language':language,'confirm':action=='setup'}).encode(),timeout=60)
            value=words.setup() if action=='setup' else words.tool(action,query,language)
            if action=='status' and welcome:
                card=words.launch_word()
                if card:value=dict(value,launch_word=card)
            return value
        except Exception as exc:return {'error':str(exc)}
    def submit():
        nonlocal operation,committed,revision,selected,top,editing,welcome
        welcome=False
        operation=ACTIONS[view] if text.strip() else 'status';committed=text
        revision+=1;selected=top=0;editing=False
    def insert(pasted):
        nonlocal text,cursor,editing,notice,welcome
        pasted=safe_text(pasted)
        if pasted:welcome=False
        limit=words.MAX_TEXT_CHARS if view==3 else words.MAX_QUERY_CHARS
        room=max(0,limit-len(text));chunk=pasted[:room]
        text=text[:cursor]+chunk+text[cursor:];cursor+=len(chunk);editing=True
        if len(chunk)<len(pasted):notice='Input limited to '+str(limit)+' characters · choose Spelling for longer text'
    def paste(pasted):
        nonlocal text,cursor,view,notice
        if not editing:text='';cursor=0
        if len(pasted)>words.MAX_QUERY_CHARS or len(pasted.split())>8:
            view=3;notice='Pasted text · Spelling selected · Enter checks it'
        insert(pasted)
    try:
        tty.setcbreak(fd);sys.stdout.write('\033[?25l\033[?2004h')
        if ui.os.environ.get('KITTY_WINDOW_ID') or ui.os.environ.get('TERM')=='xterm-kitty':sys.stdout.write('\x1b_Ga=d,d=a,q=2\x1b\\')
        while True:
            width,height=ui.shutil.get_terminal_size((90,30));width=max(20,width)
            key=(operation,committed,node,language,revision)
            value=work.get(key,lambda action=operation,query=committed:run(action,query),{'loading':True},ttl=float('inf')) or {'error':'Reference operation failed'}
            if key!=request_key:request_key=key;selected=top=0
            items=entries(value,view);flat=[]
            card=value.get('launch_word') if welcome else None
            if card:
                items.insert(0,{'title':'WORD OF THIS LAUNCH · '+card['word'],
                    'detail':card['part_of_speech']+' · '+card['definition']+'\n'+card['source'],
                    'target':card['word'],'copy':card['word']+' — '+card['definition']})
            for index,item in enumerate(items):
                for number,line in enumerate([item['title'],*item.get('detail','').splitlines()]):
                    for wrapped in clipboard_shelf.wrap_cells(safe_text(line),max(1,width-4)):
                        flat.append((index,wrapped,number==0))
            selected=max(0,min(selected,len(flat)-1));item_index=flat[selected][0];item=items[item_index]
            controls=('Enter search/check · Esc results/actions · Ctrl-U clear · Ctrl-Y clips · Tab next view' if editing else
                '/ edit search · 1 meaning · 2 synonyms · 3 antonyms · 4 spelling · 5 patterns\n↑↓ scroll · Shift-arrows page/ends · Enter open/use · b back · y copy item · c copy text\np paste · Z clips · a accept word · S setup · W shell pane · ? help · Esc close')
            if not editing and (width<55 or height<20) and not help_visible:controls='/ search · 1–5 views · Tab next view · y copy · W pane · ? help · Esc close'
            if help_visible:controls+='\n/ edits the query; Ctrl-U clears it · p pastes clipboard · Z/Ctrl-Y opens LK Clip · a accepts a flagged word · c copies working text'
            if pane_help:controls+='\n'+' · '.join(terminal_style.pane_shortcuts())
            foot=ui._media_hints(controls,width).splitlines()[:max(1,height-6)];page=max(1,height-len(foot)-6)
            if selected<top:top=selected
            elif selected>=top+page:top=selected-page+1
            top=max(0,min(top,max(0,len(flat)-page)))
            tabs=' · '.join(str(i+1)+' '+(name.upper() if i==view else name.lower()) for i,name in enumerate(VIEWS))
            frame=[ui._c('LOOK WORDS','1;36')+' · '+('node '+safe_text(node) if node else 'LOCAL / OFFLINE'),ui._c(tabs,'33'),
                   ui._c(('EDIT › ' if editing else 'QUERY › ')+input_line(text,cursor,width-9) if text or editing else 'QUERY › type a word, or / to search','1;36'),
                   ui._c(safe_text(str(value.get('source') or value.get('edition') or VIEWS[view])),'2')]
            colors=terminal_style.list_colors()
            for pos,(index,line,title) in enumerate(flat[top:top+page],top):
                styled=ui._c(('› ' if pos==selected else '  ')+line,'1;36' if title else '2')
                frame.append(terminal_style.list_row(styled,width,index,index==item_index,colors))
            frame+=['']*max(0,page+4-len(frame))
            frame += [ui._c(safe_text(notice),'33'),*foot]
            rendered=ui._terminal_frame_payload('\n'.join(ui._ansi_clip(line,width) for line in frame))
            identity=(width,height,rendered)
            if identity!=last:sys.stdout.write(rendered);sys.stdout.flush();last=identity
            pressed=ui._read_tty_key(fd,.15)
            if not pressed:continue
            last=None
            if pressed=='\x03':return 0
            if pressed.startswith('paste:'):paste(pressed[6:]);continue
            if pressed=='\x19' or (pressed=='Z' and not editing):
                pasted=clipboard_shelf.show(insert=True,fd=fd)
                if pasted is not None:paste(pasted)
                tty.setcbreak(fd);sys.stdout.write('\033[?25l\033[?2004h');continue
            if editing:
                if pressed=='esc':text=committed;cursor=len(text);editing=False;continue
                if pressed in {'enter','\r','\n'}:submit();continue
                if pressed=='\t':view=(view+1)%len(VIEWS);continue
                if pressed in {'\b','\x7f'}:
                    if cursor:text=text[:cursor-1]+text[cursor:];cursor-=1
                elif pressed=='delete':text=text[:cursor]+text[cursor+1:]
                elif pressed=='left':cursor=max(0,cursor-1)
                elif pressed=='right':cursor=min(len(text),cursor+1)
                elif pressed in {'home','\x01'}:cursor=0
                elif pressed in {'end','\x05'}:cursor=len(text)
                elif pressed=='wordleft':
                    match=re.search(r'\S+\s*$',text[:cursor]);cursor=match.start() if match else 0
                elif pressed=='wordright':
                    match=re.search(r'\s*\S+',text[cursor:]);cursor+=match.end() if match else len(text)-cursor
                elif pressed=='\x15':text='';cursor=0
                elif len(pressed)==1 and pressed.isprintable():insert(pressed)
                continue
            if pressed=='esc':return 0
            if pressed=='/':editing=True;cursor=len(text)
            elif pressed in {'1','2','3','4','5','\t'}:
                view=(view+1)%len(VIEWS) if pressed=='\t' else int(pressed)-1
                submit()
            elif pressed=='b' and history:text,view=history.pop();cursor=len(text);submit()
            elif pressed=='W':notice=terminal_style.open_pane(Path.cwd());pane_help=notice.startswith('Shell opened beside LOOK')
            elif pressed=='?':help_visible=not help_visible
            elif pressed=='p':
                pasted=clipboard_shelf.read_clipboard()
                if pasted is None:notice='System clipboard unavailable · use Z for LK Clip'
                else:paste(pasted)
            elif pressed=='y':notice=copy(item.get('copy') or item['title'])
            elif pressed=='c':notice=copy(text) if text else 'No working text to copy'
            elif pressed=='a' and item.get('issue'):
                if node:notice='Personal vocabulary is local · add this word on the intended node'
                else:
                    try:words.add_personal(item['issue']);notice='Accepted '+item['issue']+' in personal vocabulary';submit()
                    except (OSError,ValueError) as exc:notice=safe_text(str(exc))
            elif pressed in {'enter','\r','\n'}:
                if item.get('replacement'):
                    text=replace_word(text,item['issue'],item['replacement']);cursor=len(text);notice='Applied '+item['replacement']+' · c copies working text';submit()
                elif item.get('target'):
                    history.append((text,view));text=item['target'];cursor=len(text);view=0;submit()
                else:editing=True;cursor=len(text)
            elif pressed=='S':
                termios.tcsetattr(fd,termios.TCSADRAIN,old);sys.stdout.write('\033[?25h')
                try:
                    import look_renderer
                    answer,cancelled=look_renderer.prompt_line('Download offline dictionary + spelling (~12 MB; ~60 MB installed)'+(' on '+node if node else '')+'? [y/N] ')
                finally:tty.setcbreak(fd);sys.stdout.write('\033[?25l\033[?2004h')
                if not cancelled and answer.casefold()=='y':operation='setup';revision+=1;notice='Installing optional reference · you can keep using the desk'
            elif pressed in {'up','down','pageup','pagedown','shiftup','shiftdown','home','end','shiftleft','shiftright'}:
                if pressed=='up':selected-=1
                elif pressed=='down':selected+=1
                elif pressed in {'pageup','shiftup'}:selected-=page
                elif pressed in {'pagedown','shiftdown'}:selected+=page
                elif pressed in {'home','shiftleft'}:selected=0
                else:selected=len(flat)-1
            elif len(pressed)==1 and pressed.isprintable():text='';cursor=0;insert(pressed)
    finally:
        work.close();termios.tcsetattr(fd,termios.TCSADRAIN,old)
        sys.stdout.write('\033[?2004l\033[?25h\033[0m\n');sys.stdout.flush()
