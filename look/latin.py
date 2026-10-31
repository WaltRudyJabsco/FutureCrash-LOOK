"""A complete offline Latin classroom. No inference, speech or network required."""
from __future__ import annotations
import argparse
import json
import os
from pathlib import Path
import random
import sqlite3
import re
import sys
import termios
import textwrap
import tty
import latin_core as core
import look_renderer
from notebook_markdown import safe_text,cell_width

SOURCE_NOTE="D'Ooge · Latin for Beginners (1911) · Project Gutenberg #18251"


def lines_for(text,width):
    """Reflow prose; preserve paradigm columns and verse indentation."""
    out=[];paragraph=[]
    def flush():
        if paragraph:out.extend(textwrap.wrap(' '.join(paragraph),width,break_long_words=True,break_on_hyphens=False));paragraph.clear()
    for line in core.clean(text).splitlines():
        if not line.strip():flush();out.append('')
        elif line.startswith('  '):flush();out.extend(textwrap.wrap(line,width,replace_whitespace=False,drop_whitespace=False) or [''])
        else:paragraph.append(safe_text(line.strip()))
    flush();return out


class Classroom:
    def __init__(self,ui,state):self.ui=ui;self.state=state;self.fd=sys.stdin.fileno();self.old=termios.tcgetattr(self.fd)
    def key(self):
        before=self.size()
        while True:
            key=self.ui._read_tty_key(self.fd,.25)
            if key:return key
            if self.size()!=before:return 'resize'
    def size(self):
        width,height=self.ui.shutil.get_terminal_size((100,30));return max(20,width),max(10,height)
    def frame(self,title,body,controls='',notice=''):
        width,height=self.size();hints=self.ui._media_hints(controls,width) if controls else ''
        reserve=2+len(hints.splitlines())+bool(notice);capacity=max(1,height-reserve)
        frame=[self.ui._c(safe_text(title),'1;36'),*body[:capacity]]
        frame+=['']*max(0,height-len(hints.splitlines())-bool(notice)-len(frame)-1)
        if hints:frame.append(hints)
        if notice:frame.append(self.ui._c(safe_text(notice),'33'))
        sys.stdout.write(self.ui._terminal_frame_payload('\n'.join(self.ui._ansi_clip(line,width) for line in frame)));sys.stdout.flush()
        return capacity
    def ask(self,label,initial=''):
        termios.tcsetattr(self.fd,termios.TCSADRAIN,self.old)
        try:
            print('\n'+self.ui._c(label,'1;36'))
            value,cancelled=look_renderer.prompt_line('› ',initial=initial)
            return None if cancelled else value.strip()
        finally:tty.setcbreak(self.fd)
    def choose(self,title,rows,label,initial=0,extra=''):
        index=initial;query=''
        while True:
            visible=[r for r in rows if core.fold(query) in core.fold(label(r))]
            width,height=self.size()
            controls='↑↓ move · Shift-arrows page/ends · Enter open · / search · Esc back' if width>=60 else '↑↓ · Shift-arrows · Enter · / · Esc'
            page=max(1,height-3-len(self.ui._media_hints(controls,width).splitlines()));index=max(0,min(index,max(0,len(visible)-1)));top=max(0,index-page+1)
            colors=self.ui.terminal_style.list_colors()
            body=[self.ui.terminal_style.list_row(('› ' if i==index else '  ')+safe_text(label(row)),width,i,i==index,colors) for i,row in enumerate(visible[top:top+page],top)]
            self.frame(title,body,controls,extra or (query and 'Search: '+query))
            key=self.key()
            if key in {'esc','q','\x03'}:return None
            if key in {'enter','\r','\n'} and visible:return visible[index]
            if key=='up':index-=1
            elif key=='down':index+=1
            elif key in {'shiftup','pageup'}:index-=page
            elif key in {'shiftdown','pagedown'}:index+=page
            elif key in {'shiftleft','home'}:index=0
            elif key in {'shiftright','end'}:index=len(visible)-1
            elif key=='/':
                text=self.ask('Filter this list',query)
                if text is not None:query=text;index=0
    def read(self,row):
        ident=row['id'];saved=self.state.lesson(ident);top=saved['page'];query='';notice='';cached=None;lines=[]
        while True:
            width,height=self.size()
            if cached!=width:lines=lines_for(row['text'],width);cached=width
            controls='↑↓ scroll · ←→ lesson · Shift-arrows page/ends · / find · n next · p practice · v words · m mark studied · Esc back' if width>=60 else '↑↓ · Shift-arrows · / · p practice · m studied · Esc'
            page=max(1,height-3-len(self.ui._media_hints(controls,width).splitlines()))
            top=max(0,min(top,max(0,len(lines)-page)))
            title=('LATIN · '+str(row['number'])+' · ' if 'number' in row else 'LATIN · ')+row['title']
            self.frame(title,lines[top:top+page],controls,notice or f'{top+1}–{min(top+page,len(lines))}/{len(lines)} · '+SOURCE_NOTE)
            key=self.key()
            if key in {'esc','q','\x03'}:self.state.save_lesson(ident,page=top);return
            if key=='up':top-=1
            elif key=='down':top+=1
            elif key in {'shiftup','pageup','b'}:top-=page
            elif key in {'shiftdown','pagedown',' '}:top+=page
            elif key in {'shiftleft','home'}:top=0
            elif key in {'shiftright','end'}:top=len(lines)
            elif key in {'left','right'} and 'number' in row:
                self.state.save_lesson(ident,page=top)
                row=core.unit(max(0,min(79,row['number']+(-1 if key=='left' else 1))))
                ident=row['id'];top=self.state.lesson(ident)['page'];cached=None;notice=''
            elif key=='m' and 'number' in row:
                studied=not self.state.lesson(ident)['studied'];self.state.save_lesson(ident,studied=studied);notice='Marked studied; practice results are tracked separately' if studied else 'Study mark cleared'
            elif key=='p' and 'number' in row:self.practice(row['number'],exact=True)
            elif key=='v' and 'number' in row:self.words(lesson=row['number'])
            elif key in {'/','n'}:
                if key=='/':
                    value=self.ask('Find in this text',query)
                    if value is None:continue
                    query=value
                if query:
                    hit=next((i for i in list(range(top+1,len(lines)))+list(range(top+1)) if core.fold(query) in core.fold(lines[i])),None)
                    if hit is None:notice='No matching passage'
                    else:top=hit;notice='Found: '+query
    def practice(self,number=None,exact=False,review=False):
        if number is None:number=core.unit(self.state.setting('last','lesson-000'))['number'] if self.state.setting('last','').startswith('lesson-') else 0
        pool=core.deck(number)
        if exact:pool=[c for c in pool if c['lesson']==number]
        if review:pool=self.state.due(pool)
        elif not exact:
            due=self.state.due(pool,new=True);pool=due if due else pool
        if not pool:
            self.ask('No cards due for this selection. Enter returns.');return
        # Include a lesson's concept check before a bounded, varied practice set.
        first=[c for c in pool if c['kind']=='choice'];others=[c for c in pool if c['kind']!='choice']
        random.shuffle(first);random.shuffle(others);cards=(first[:1]+others[:11]+first[1:])[:12]
        for index,card in enumerate(cards,1):
            width,height=self.size();body=lines_for(card['prompt'],width)+['']
            options=list(card.get('options',[]));random.shuffle(options)
            if options:body += [str(i+1)+'. '+value for i,value in enumerate(options)]
            self.frame(f'LATIN PRACTICE · {index}/{len(cards)} · lesson {card["lesson"]}',body,'Enter answer · Esc returns', 'Macrons '+('required' if self.state.setting('strict')=='1' else 'optional')+' · typed drills use uncontracted textbook forms')
            if card['kind']=='word':
                value=self.ask('Recall the meaning, then Enter reveals it · Esc cancels')
                if value is None:return
                self.frame('VOCABULARY · self-assessed',lines_for(card['prompt']+'\n\n'+card['answers'][0],width),'1 review again · 2 recalled · Esc back')
                while True:
                    key=self.key()
                    if key in {'esc','q','\x03'}:return
                    if key in {'1','2'}:self.state.grade(card['id'],key=='2');break
                continue
            question=card['prompt']+'\n'+('\n'.join(str(i+1)+'. '+option for i,option in enumerate(options)) if options else '')
            value=self.ask(question+'\n'+('Option number' if options else 'Latin form · blank reveals answer'))
            if value is None:return
            correct=(value.isdigit() and 0<int(value)<=len(options) and options[int(value)-1]==card['answers'][0]) if options else core.accepted(value,card,self.state.setting('strict')=='1')
            self.state.grade(card['id'],bool(correct))
            message=('Correct' if correct else 'Review this one')+'\n\n'+card['why']
            self.frame('LATIN · FEEDBACK',lines_for(message,width),'Enter next · Esc back')
            while True:
                key=self.key()
                if key in {'esc','q','\x03'}:return
                if key in {'enter','\r','\n',' '}:break
    def words(self,query='',lesson=None):
        rows=core.lesson_words().get(lesson,[]) if lesson is not None else core.vocabulary()
        if query:rows=[r for r in rows if core.fold(query) in core.fold(r['latin']+' '+r['definition'])]
        if not rows:self.ask('No vocabulary entries in this selection · Enter returns');return
        while True:
            row=self.choose('LATIN · VOCABULARY',rows,lambda r:r['latin']+' · '+r['definition'])
            if row is None:return
            self.read({'id':'dictionary-'+row['id'],'title':row['latin'],'text':row['latin']+'\n\n'+row['definition']})
    def home(self):
        while True:
            summary=self.state.summary();last=self.state.setting('last','lesson-000')
            if not last.startswith('lesson-'):last='lesson-000'
            options=[('continue','Continue · '+core.unit(last)['title']),('course','Course · pronunciation + 79 lessons'),('practice','Practice · current lesson and earlier material'),('review','Review · due cards'),('words','Words · searchable Latin–English dictionary'),('grammar','Grammar · tables, syntax, index and English–Latin dictionary'),('read','Readings · stories and connected prose'),('progress','Progress and settings'),('about','About, source and help')]
            selected=self.choose('LK LATIN · OFFLINE CLASSROOM',[{'id':i,'title':t} for i,t in options],lambda r:r['title'],extra=f'{summary["studied"]}/80 units marked studied · {summary["attempts"]} reviews · no audio or AI')
            if selected is None:return 0
            action=selected['id']
            if action=='continue':self.read(core.unit(last))
            elif action=='course':
                row=self.choose('LATIN · COURSE',core.course()['units'],lambda r:('✓ ' if self.state.lesson(r['id'])['studied'] else '  ')+str(r['number']).rjust(2)+' · '+r['title'])
                if row:self.read(row)
            elif action=='practice':self.practice()
            elif action=='review':self.practice(review=True)
            elif action=='words':self.words()
            elif action=='grammar':
                query=self.ask('Search grammar across lessons/reference · Enter browses reference sections')
                if query is None:continue
                matches=core.search(query) if query else core.course()['references'][1:]
                row=self.choose('LATIN · REFERENCE',matches,lambda r:r['title'])
                if row:self.read(row)
            elif action=='read':self.read(core.course()['references'][0])
            elif action=='progress':
                text=json.dumps(summary,indent=2)+'\n\nStudy marks record reading, not mastery.\nReview totals include self-assessed vocabulary.\nMacrons are '+('required' if self.state.setting('strict')=='1' else 'optional')+'.'
                self.read({'id':'progress','title':'Progress','text':text})
                answer=self.ask('Macron checking: 1 require · 0 optional · Enter keeps current')
                if answer in {'0','1'}:self.state.set('strict',answer)
            else:self.read({'id':'about','title':'About LK Latin','text':ABOUT})


ABOUT="""LK Latin is an offline study environment around Benjamin L. D'Ooge's Latin for Beginners (1911), Project Gutenberg eBook 18251. The complete supplied text and its licence are bundled. This is an historical school textbook: its Roman-war narratives and social assumptions reflect its period. LOOK adds navigation, original concept checks, morphology drills and local spaced review; it does not silently rewrite the source.

Start with pronunciation (unit 0), then proceed through lessons 1–79. All lessons and references remain open for browsing. Read the explanations, work through the book's exercises, and use p for checked practice. Mark a unit studied with m when you choose. A study mark is not a certification of mastery.

Typed morphology and numbered concept checks are automatically checked. Vocabulary recall is self-assessed after revealing the definition. Open-ended textbook translations and appendix exercises are self-assessed; there is no AI grading or invented answer key. Standard uncontracted textbook forms are requested in typed verb drills; known listed alternatives are accepted. Macrons are optional by default; strict checking can be enabled in Progress.

Practice draws from the current lesson and earlier material. Review schedules correct cards at 1, 3, 7, 14, 30 and 60 days; missed cards return after ten minutes. Progress and reading position stay on this computer in ~/.local/share/look/latin. There is no account, network, speech dependency or automatic Fabric synchronization.

Controls: arrows move; Shift-Up/Down page; Shift-Left/Right go to ends; Enter opens; Esc returns. In a text: / finds, n finds next, p practices its lesson, v opens its words, m toggles studied. Answer fields use the existing Unicode editor; Esc cancels without grading. Close the classroom with Esc from its home.

Source: https://www.gutenberg.org/ebooks/18251
The source text's final section contains the complete Project Gutenberg licence and credits.
"""


def main(argv=None,ui=None):
    parser=argparse.ArgumentParser(prog='lk latin',description=__doc__)
    parser.add_argument('action',nargs='?',default='home',choices=['home','list','lesson','practice','review','words','grammar','read','progress','about','export'])
    parser.add_argument('query',nargs='*');parser.add_argument('--lesson',type=int);parser.add_argument('--json',action='store_true');parser.add_argument('--strict-macrons',choices=['on','off'])
    args=parser.parse_args(argv)
    try:
        if args.lesson is not None:core.unit(args.lesson)
        if args.action=='list':
            rows=[{k:r[k] for k in ('id','number','title')} for r in core.course()['units']]
            print(json.dumps(rows,ensure_ascii=False,indent=2) if args.json else '\n'.join(str(r['number']).rjust(2)+' · '+r['title'] for r in rows));return 0
        if args.action=='about':print(ABOUT);return 0
        if args.action=='lesson':row=core.unit(' '.join(args.query) or args.lesson or 0)
        elif args.action=='read':row=core.course()['references'][0]
        elif args.action=='grammar':
            matches=core.search(' '.join(args.query)) if args.query else core.course()['references'][1:]
            if args.json:print(json.dumps([{k:r[k] for k in ('id','title')} for r in matches],ensure_ascii=False));return 0
            if not (sys.stdin.isatty() and sys.stdout.isatty()):
                print('\n\n'.join(r['title']+'\n'+core.clean(r['text']) for r in matches));return 0
        elif args.action=='words' and not (sys.stdin.isatty() and sys.stdout.isatty()):
            query=core.fold(' '.join(args.query));rows=[r for r in core.vocabulary() if query in core.fold(r['latin']+' '+r['definition'])]
            print(json.dumps(rows,ensure_ascii=False,indent=2) if args.json else '\n'.join(r['latin']+' · '+r['definition'] for r in rows));return 0
        if args.action in {'lesson','read'} and not (sys.stdin.isatty() and sys.stdout.isatty()):print(core.clean(row['text']));return 0
        state=core.Progress()
        try:
            if args.strict_macrons:state.set('strict','1' if args.strict_macrons=='on' else '0')
            if args.action=='progress':print(json.dumps(state.summary(),indent=2) if args.json else 'Latin · '+str(state.summary()['studied'])+'/80 units studied · '+str(state.summary()['attempts'])+' reviews');return 0
            if args.action=='export':
                if len(args.query)!=1:raise ValueError('Use lk latin export FILE.json')
                path=Path(args.query[0]).expanduser()
                with os.fdopen(os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600),'w') as stream:json.dump({'summary':state.summary(),'lessons':[dict(r) for r in state.db.execute('SELECT * FROM lessons')],'cards':[dict(r) for r in state.db.execute('SELECT * FROM cards')],'settings':[dict(r) for r in state.db.execute('SELECT * FROM settings')]},stream,ensure_ascii=False,indent=2)
                print('Exported '+str(path));return 0
            if not ui or not (sys.stdin.isatty() and sys.stdout.isatty()):raise ValueError('Use an interactive terminal for the classroom; list, lesson, words, grammar and progress also support text output')
            classroom=Classroom(ui,state)
            try:
                tty.setcbreak(classroom.fd)
                if os.environ.get('KITTY_WINDOW_ID') or os.environ.get('TERM')=='xterm-kitty':sys.stdout.write('\x1b_Ga=d,d=a,q=2\x1b\\')
                if args.action=='home':return classroom.home()
                if args.action in {'lesson','read'}:classroom.read(row)
                elif args.action in {'practice','review'}:classroom.practice(args.lesson,review=args.action=='review')
                elif args.action=='words':classroom.words(' '.join(args.query))
                elif args.action=='grammar':
                    selected=classroom.choose('LATIN · GRAMMAR',matches,lambda r:r['title'])
                    if selected:classroom.read(selected)
                return 0
            finally:termios.tcsetattr(classroom.fd,termios.TCSADRAIN,classroom.old);sys.stdout.write('\x1b[0m\n');sys.stdout.flush()
        finally:state.close()
    except (OSError,ValueError,KeyError,sqlite3.Error) as exc:print('Latin: '+safe_text(str(exc)));return 1
