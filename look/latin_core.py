"""Offline Latin course indexing, checked forms and local spaced review."""
from __future__ import annotations
from functools import lru_cache
import hashlib
import json
from pathlib import Path
import re
import sqlite3
import time
import unicodedata
import latin_data
from latin_course import TEXT

CASES=('nominative','genitive','dative','accusative','ablative','vocative')
PERSONS=('first singular','second singular','third singular','first plural','second plural','third plural')
REVIEW_DAYS=(1,3,7,14,30,60)


def fold(text,strict=False):
    text=str(text).casefold().replace('æ','ae').replace('œ','oe').replace('j','i').replace('v','u')
    if not strict:text=''.join(c for c in unicodedata.normalize('NFD',text) if not unicodedata.combining(c))
    return ' '.join(re.sub(r'[^\w\s\u0300-\u036f]',' ',unicodedata.normalize('NFC',text)).split())


def clean(text):return str(text).replace('«','').replace('»','').replace('_','')


def roman(text):
    values={'I':1,'V':5,'X':10,'L':50,'C':100,'D':500,'M':1000};result=previous=0
    for char in reversed(text):
        value=values[char];result+=-value if value<previous else value;previous=max(previous,value)
    return result


@lru_cache(maxsize=1)
def course():
    text=TEXT;headings=list(re.finditer(r'^LESSON ([IVXLCDM]+)$',text,re.M))
    if len(headings)!=79:raise ValueError('Latin course text is incomplete; reinstall LOOK')
    reading=text.index('\nREADING MATTER\n',headings[-1].end())
    pronunciation=text.index('\nPART I\n',text.index('TO THE STUDENT',12000)) if '\nPART I\n' in text else 0
    units=[{'id':'lesson-000','number':0,'title':'Pronunciation, syllables, quantity and accent','text':text[pronunciation:headings[0].start()].strip()}]
    for i,match in enumerate(headings):
        body=text[match.end():headings[i+1].start() if i+1<len(headings) else reading].strip()
        title=clean(body.split('\n\n',1)[0].replace('\n',' ')).capitalize()
        units.append({'id':f'lesson-{roman(match[1]):03}','number':roman(match[1]),'title':title,'text':body})
    markers=[('readings','Readings',reading),('appendix-1','Grammar tables and paradigms',text.index('\nAPPENDIX I\n',reading)),
             ('appendix-2','Syntax and construction reference',text.index('\nAPPENDIX II\n',reading)),
             ('appendix-3','Review exercises',text.index('\nAPPENDIX III\n',reading)),
             ('special','Lesson vocabularies',text.index('\nSPECIAL VOCABULARIES\n',reading)),
             ('latin-english','Latin–English dictionary',text.index('\nLATIN-ENGLISH VOCABULARY\n',reading)),
             ('english-latin','English–Latin dictionary',text.index('\nENGLISH-LATIN VOCABULARY\n',reading)),
             ('index','Grammar index',text.index('\nINDEX\n',reading)),
             ('license','Source and licence',text.index('*** END OF THE PROJECT GUTENBERG',reading))]
    refs=[]
    for i,(ident,title,start) in enumerate(markers):
        end=markers[i+1][2] if i+1<len(markers) else len(text)
        refs.append({'id':ident,'title':title,'text':text[start:end].strip()})
    # Retain the entire supplied edition, including its licence and source credit.
    return {'units':units,'references':refs,'text':text}


def unit(value):
    try:number=int(str(value).removeprefix('lesson-'))
    except ValueError:raise ValueError('Choose a lesson number from 0 to 79')
    if not 0<=number<=79:raise ValueError('Choose a lesson number from 0 to 79')
    return course()['units'][number]


def entries(text,indent=0):
    text=re.sub(r'(?m)^ *(?:NOUNS?|ADJECTIVES?|ADVERBS?|VERBS?|CONJUNCTIONS?|PREPOSITIONS?|PRONOUNS?) *$','',text)
    matches=list(re.finditer(r'^ {'+str(indent)+r'}«([^»]+)»',text,re.M));rows=[]
    for i,match in enumerate(matches):
        body=text[match.end():matches[i+1].start() if i+1<len(matches) else len(text)]
        body=re.sub(r'\n\n[A-Z]\s*$','',body).strip(' ,\n')
        if not body:continue
        head=clean(match[1]);description=clean(' '.join(body.split()))
        rows.append({'id':hashlib.sha256((head+'\n'+description).encode()).hexdigest()[:20], 'latin':head,'definition':description})
    return rows


@lru_cache(maxsize=1)
def vocabulary():
    section=next(r for r in course()['references'] if r['id']=='latin-english')
    return entries(section['text'])


@lru_cache(maxsize=1)
def lesson_words():
    text=next(r for r in course()['references'] if r['id']=='special')['text']
    marks=list(re.finditer(r'^LESSON ([IVXLCDM]+),[^\n]*',text,re.M));result={}
    for i,mark in enumerate(marks):
        body=text[mark.end():marks[i+1].start() if i+1<len(marks) else len(text)]
        result[roman(mark[1])]=entries(body,2)
    return result


def checks():
    rows=[]
    for line in latin_data.CHECKS.strip().splitlines():
        number,prompt,answer,w1,w2,w3,why=line.split('|')
        rows.append({'id':'check-'+number,'lesson':int(number),'kind':'choice','prompt':prompt,'answers':[answer], 'options':[answer,w1,w2,w3],'why':why})
    return rows


@lru_cache(maxsize=1)
def forms():
    rows=[]
    def add(lemma,lesson,tag,labels,values):
        for i,(label,value) in enumerate(zip(labels,values)):
            rows.append({'id':'form-'+lemma+'-'+tag+'-'+str(i),'lesson':lesson,'kind':'form',
                         'prompt':lemma+' · '+tag+' · '+label,'answers':value.split('/'),
                         'why':'Textbook form: '+value.replace('/',' or ')+'. See the grammar tables for the full paradigm.'})
    for lemma,lesson,singular,plural in latin_data.NOUNS:
        add(lemma,lesson,'singular',CASES,singular.split());add(lemma,lesson,'plural',CASES,plural.split())
    for lemma,lesson,infinitive,present,perfect,subj,pres,passive in latin_data.VERBS:
        add(lemma,lesson,'present indicative active',PERSONS,pres.split())
        imperfect=present if lemma in {'amō','moneō'} else ('regē' if lemma=='regō' else present+'ē')
        add(lemma,20 if lesson==19 else 24 if lesson==23 else 26,'imperfect indicative active',PERSONS,[imperfect+e for e in ('bam','bās','bat','bāmus','bātis','bant')])
        future=[present+e for e in ('bō','bis','bit','bimus','bitis','bunt')] if lemma in {'amō','moneō'} else [present+e for e in ('am','ēs','et','ēmus','ētis','ent')]
        add(lemma,21 if lesson==19 else 25 if lesson==23 else 26,'future indicative active',PERSONS,future)
        add(lemma,27 if lesson==19 else 28 if lesson==23 else 29,'present indicative passive',PERSONS,passive.split())
        for tag,level,endings in [('perfect',32,'ī istī it imus istis ērunt/ēre'),('pluperfect',33,'eram erās erat erāmus erātis erant'),('future perfect',33,'erō eris erit erimus eritis erint'),('perfect subjunctive',64,'erim erīs erit erīmus erītis erint'),('pluperfect subjunctive',64,'issem issēs isset issēmus issētis issent')]:
            values=['/'.join(perfect+e for e in ending.split('/')) for ending in endings.split()]
            add(lemma,level,tag+(' active' if 'subjunctive' in tag else ' indicative active'),PERSONS,values)
        endings=('em','ēs','et','ēmus','ētis','ent') if lemma=='amō' else ('am','ās','at','āmus','ātis','ant')
        add(lemma,61,'present subjunctive active',PERSONS,[subj+e for e in endings])
        add(lemma,63,'imperfect subjunctive active',PERSONS,[infinitive[:-1]+e for e in ('em','ēs','et','ēmus','ētis','ent')])
    for tag,level,values in [('present',18,'sum es est sumus estis sunt'),('imperfect',18,'eram erās erat erāmus erātis erant'),('future',18,'erō eris erit erimus eritis erunt'),('perfect',31,'fuī fuistī fuit fuimus fuistis fuērunt/fuēre'),('pluperfect',31,'fueram fuerās fuerat fuerāmus fuerātis fuerant'),('future perfect',31,'fuerō fueris fuerit fuerimus fueritis fuerint')]:
        add('sum',level,tag+' indicative',PERSONS,values.split())
    return rows


def accepted(answer,card,strict=False):return any(fold(answer,strict)==fold(value,strict) for value in card['answers'])


def deck(through=79):
    rows=[*checks(),*forms()]
    for number,words in lesson_words().items():
        rows += [dict(w,id='word-'+str(number)+'-'+w['id'],lesson=number,kind='word',prompt=w['latin'],answers=[w['definition']],why='Self-assessed vocabulary recall; see the dictionary for full usage.') for w in words]
    return [r for r in rows if r['lesson']<=through]


def search(query,kind='all'):
    terms=fold(query).split();matches=[]
    groups=course()['units']+course()['references'] if kind=='all' else course()['units'] if kind=='lessons' else course()['references']
    for row in groups:
        if all(t in fold(row['title']+' '+row['text']) for t in terms):matches.append(row)
    return matches


class Progress:
    def __init__(self,path=None):
        self.path=Path(path) if path else Path.home()/'.local/share/look/latin/progress.sqlite3'
        self.path.parent.mkdir(parents=True,exist_ok=True,mode=0o700)
        self.db=sqlite3.connect(self.path,timeout=3);self.db.row_factory=sqlite3.Row
        self.path.chmod(0o600)
        self.db.executescript('''CREATE TABLE IF NOT EXISTS lessons(id TEXT PRIMARY KEY,studied INTEGER DEFAULT 0,page INTEGER DEFAULT 0);
            CREATE TABLE IF NOT EXISTS cards(id TEXT PRIMARY KEY,attempts INTEGER,correct INTEGER,streak INTEGER,due REAL,last REAL);
            CREATE TABLE IF NOT EXISTS settings(key TEXT PRIMARY KEY,value TEXT);''')
    def close(self):self.db.close()
    def setting(self,key,default=''):
        row=self.db.execute('SELECT value FROM settings WHERE key=?',(key,)).fetchone();return row[0] if row else default
    def set(self,key,value):
        with self.db:self.db.execute('INSERT OR REPLACE INTO settings VALUES (?,?)',(key,str(value)))
    def lesson(self,ident):
        row=self.db.execute('SELECT * FROM lessons WHERE id=?',(ident,)).fetchone();return dict(row) if row else {'id':ident,'studied':0,'page':0}
    def save_lesson(self,ident,*,page=None,studied=None):
        old=self.lesson(ident)
        with self.db:self.db.execute('INSERT OR REPLACE INTO lessons VALUES (?,?,?)',(ident,old['studied'] if studied is None else int(studied),old['page'] if page is None else max(0,page)))
        if ident.startswith('lesson-'):self.set('last',ident)
    def grade(self,ident,correct,now=None):
        now=time.time() if now is None else now
        with self.db:
            self.db.execute('BEGIN IMMEDIATE')
            old=self.db.execute('SELECT * FROM cards WHERE id=?',(ident,)).fetchone()
            attempts=(old['attempts'] if old else 0)+1;right=(old['correct'] if old else 0)+int(correct)
            streak=(old['streak'] if old else 0)+1 if correct else 0
            due=now+(REVIEW_DAYS[min(streak-1,len(REVIEW_DAYS)-1)]*86400 if correct else 600)
            self.db.execute('INSERT OR REPLACE INTO cards VALUES (?,?,?,?,?,?)',(ident,attempts,right,streak,due,now))
        return due
    def due(self,cards,now=None,new=False):
        now=time.time() if now is None else now;seen={r['id']:dict(r) for r in self.db.execute('SELECT * FROM cards')}
        return sorted([c for c in cards if (c['id'] in seen and seen[c['id']]['due']<=now) or (new and c['id'] not in seen)],key=lambda c:(seen.get(c['id'],{}).get('due',now),c['lesson'],c['id']))
    def summary(self):
        return {'studied':self.db.execute('SELECT count(*) FROM lessons WHERE studied=1').fetchone()[0],
                'attempts':self.db.execute('SELECT coalesce(sum(attempts),0) FROM cards').fetchone()[0],
                'correct':self.db.execute('SELECT coalesce(sum(correct),0) FROM cards').fetchone()[0],
                'last':self.setting('last','lesson-000')}
