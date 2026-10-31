"""Portable offline English reference; explicit setup, indexed reads, system fallbacks."""
from __future__ import annotations
import argparse
import contextlib
import difflib
import fnmatch
import fcntl
import secrets
import functools
import io
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import unicodedata
import urllib.parse
import urllib.request
import zipfile

EDITION='Open English WordNet 2025'
SOURCE='https://en-word.net/'
DOWNLOAD=SOURCE+'static/english-wordnet-2025-json.zip'
SHA256='7d749f6e2c39e6970e4997839dcf6e42fd281f3c2fae0171d2192bae8cfa4b51'
MAX_DOWNLOAD_BYTES=16*1024*1024
MAX_UNPACKED_BYTES=100*1024*1024
SPELL_URL='https://files.pythonhosted.org/packages/cd/19/ce6fcb4b86e188983bcfc1f84e4ac6f3038ca8d68b6d70a678cdc566f66c/spylls-0.1.7-py2.py3-none-any.whl'
SPELL_SHA256='0c7fa4b66615f390bd12fd37939b85934c012309fd3cce8584844c54270b7776'
MAX_QUERY_CHARS=200
MAX_TEXT_CHARS=4000
MAX_CHECK_WORDS=50
SCHEMA=1
ATTRIBUTION='Open English WordNet team, CC BY 4.0; derived from Princeton WordNet (WordNet License).'
LICENCE_URL='https://github.com/globalwordnet/english-wordnet/blob/main/LICENSE.md'
POS={'n':'noun','v':'verb','a':'adjective','s':'adjective','r':'adverb'}


def root():return Path.home()/'.local/share/look/words'
def database():return root()/'english.sqlite3'
def personal_path():return Path.home()/'.config/look/personal-words.txt'
def normalize(text):return unicodedata.normalize('NFC',text).casefold().strip().replace('_',' ')


def query_text(value,limit=MAX_QUERY_CHARS):
    if not isinstance(value,str) or not value.strip() or len(value)>limit or any(unicodedata.category(c)=='Cc' and c not in '\n\t' for c in value):
        raise ValueError('Enter readable text, at most '+str(limit)+' characters')
    return value.strip()


class Redirects(urllib.request.HTTPRedirectHandler):
    def redirect_request(self,req,fp,code,msg,headers,newurl):
        parsed=urllib.parse.urlsplit(newurl)
        if parsed.scheme!='https' or parsed.hostname not in {'en-word.net','files.pythonhosted.org'}:raise ValueError('Word reference download left its official HTTPS host')
        return super().redirect_request(req,fp,code,msg,headers,newurl)


def build_database(archive,destination):
    """Build a replacement beside the current index; never overwrite a working one halfway."""
    with zipfile.ZipFile(archive) as bundle:
        if len(bundle.infolist())>100 or sum(i.file_size for i in bundle.infolist())>MAX_UNPACKED_BYTES:
            raise ValueError('Word reference exceeds expected size')
        with sqlite3.connect(destination) as db:
            db.executescript('''CREATE TABLE meta(key TEXT PRIMARY KEY,value TEXT);
                CREATE TABLE synsets(id TEXT PRIMARY KEY,payload TEXT);
                CREATE TABLE senses(id TEXT PRIMARY KEY,word TEXT,lemma TEXT,synset TEXT,antonyms TEXT);
                CREATE TABLE forms(word TEXT,lemma TEXT);
                CREATE TABLE vocabulary(word TEXT PRIMARY KEY,label TEXT);''')
            for name in bundle.namelist():
                if not name.endswith('.json'):continue
                data=json.loads(bundle.read(name))
                if not isinstance(data,dict):raise ValueError('Invalid dictionary section')
                if name.startswith('entries-'):
                    for lemma,parts in data.items():
                        word=normalize(lemma)
                        db.execute('INSERT OR IGNORE INTO vocabulary VALUES(?,?)',(word,lemma))
                        for entry in parts.values():
                            for form in entry.get('form',[]):
                                db.execute('INSERT INTO forms VALUES(?,?)',(normalize(form),word))
                                db.execute('INSERT OR IGNORE INTO vocabulary VALUES(?,?)',(normalize(form),form))
                            for sense in entry.get('sense',[]):
                                db.execute('INSERT INTO senses VALUES(?,?,?,?,?)',(sense['id'],word,lemma,sense['synset'],json.dumps(sense.get('antonym',[]))))
                else:
                    for ident,sense in data.items():
                        selected={k:sense[k] for k in ('definition','example','members','partOfSpeech','hypernym','hyponym','similar') if k in sense}
                        db.execute('INSERT INTO synsets VALUES(?,?)',(ident,json.dumps(selected,ensure_ascii=False)))
            db.executescript('CREATE INDEX sense_word ON senses(word); CREATE INDEX form_word ON forms(word);')
            for key,value in {'schema':str(SCHEMA),'edition':EDITION,'source':SOURCE,'sha256':SHA256,'attribution':ATTRIBUTION,'licence_url':LICENCE_URL}.items():
                db.execute('INSERT INTO meta VALUES(?,?)',(key,value))
            count=db.execute('SELECT count(*) FROM synsets').fetchone()[0]
            if not count:raise ValueError('Dictionary has no definitions')
            if db.execute('SELECT count(*) FROM senses s LEFT JOIN synsets t ON s.synset=t.id WHERE t.id IS NULL').fetchone()[0]:
                raise ValueError('Dictionary contains unresolved definitions')
    return count


def download(url,checksum):
    request=urllib.request.Request(url,headers={'User-Agent':'FutureCrash-LOOK offline word reference'})
    with urllib.request.build_opener(Redirects()).open(request,timeout=30) as response:
        data=response.read(MAX_DOWNLOAD_BYTES+1)
    if len(data)>MAX_DOWNLOAD_BYTES or hashlib.sha256(data).hexdigest()!=checksum:
        raise ValueError('Word reference failed its pinned size/checksum check; existing dictionary kept')
    return data


def install_spelling(data,destination):
    with zipfile.ZipFile(io.BytesIO(data)) as bundle:
        if sum(i.file_size for i in bundle.infolist())>MAX_UNPACKED_BYTES:raise ValueError('Spelling package exceeds expected size')
        for member in bundle.infolist():
            path=Path(member.filename)
            if path.is_absolute() or '..' in path.parts:raise ValueError('Invalid spelling package path')
            if not member.filename.startswith(('spylls/','spylls-0.1.7.dist-info/')) or member.is_dir():continue
            target=destination/path;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(bundle.read(member))
    if not (destination/'spylls/hunspell/data/en/en_US.dic').is_file():raise ValueError('English spelling dictionary missing')


def setup():
    root().mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.setup-',dir=root()) as folder:
        folder=Path(folder);archive=folder/'download.zip';target=folder/'english.sqlite3'
        archive.write_bytes(download(DOWNLOAD,SHA256))
        count=build_database(archive,target)
        spelling=root()/'spylls-0.1.7'
        if not spelling.is_dir():
            install_spelling(download(SPELL_URL,SPELL_SHA256),folder/'spelling')
            os.replace(folder/'spelling',spelling)
        os.replace(target,database())
    portable_spelling.cache_clear()
    return dict(status(),installed=True,definitions=count)


@contextlib.contextmanager
def connection():
    path=database()
    if not path.is_file():yield None;return
    db=sqlite3.connect(path.as_uri()+'?mode=ro',uri=True)
    try:
        if db.execute("SELECT value FROM meta WHERE key='schema'").fetchone()!= (str(SCHEMA),):raise ValueError('Unsupported word reference; run lk words setup')
        yield db
    finally:db.close()


def status():
    with connection() as db:
        metadata=dict(db.execute('SELECT key,value FROM meta')) if db else {}
    return {'installed':bool(metadata),'edition':metadata.get('edition'),'source':metadata.get('source'),
            'bytes':database().stat().st_size if metadata else 0,
            'portable_spelling':(root()/'spylls-0.1.7/spylls/hunspell/data/en/en_US.dic').is_file(),
            'system':{name:shutil.which(name) for name in ('hunspell','aspell','wn')},
            'system_wordlists':[str(p) for p in system_wordlists() if p.is_file()],
            'hint':'lk words setup downloads about 12 MB once; lookups never use the network'}


def system_definition(word):
    executable=shutil.which('wn')
    if not executable:return ''
    try:result=subprocess.run([executable,word,'-over'],capture_output=True,text=True,timeout=3)
    except (OSError,subprocess.TimeoutExpired):return ''
    return result.stdout[:16000].strip() if result.returncode>=0 and 'Overview of ' in result.stdout else ''


def example_text(value):
    if isinstance(value,str):return value
    if isinstance(value,dict) and isinstance(value.get('text'),str):
        return value['text']+(' — '+value['source'] if isinstance(value.get('source'),str) else '')
    return ''


def lookup(word):
    word=query_text(word);key=normalize(word);results=[]
    with connection() as db:
        if db:
            lemmas=[key,*[r[0] for r in db.execute('SELECT lemma FROM forms WHERE word=?',(key,))]]
            seen=set()
            for lemma in dict.fromkeys(lemmas):
                for ident,label,synset,antonyms in db.execute('SELECT id,lemma,synset,antonyms FROM senses WHERE word=? LIMIT 30',(lemma,)):
                    if synset in seen:continue
                    seen.add(synset)
                    sense=json.loads(db.execute('SELECT payload FROM synsets WHERE id=?',(synset,)).fetchone()[0])
                    opposites=[]
                    for opposite in json.loads(antonyms):
                        row=db.execute('SELECT lemma FROM senses WHERE id=?',(opposite,)).fetchone()
                        if row:opposites.append(row[0])
                    related={}
                    for relation in ('hypernym','hyponym','similar'):
                        values=[]
                        for target in sense.get(relation,[])[:8]:
                            row=db.execute('SELECT payload FROM synsets WHERE id=?',(target,)).fetchone()
                            if row:values+=json.loads(row[0]).get('members',[])[:3]
                        if values:related[relation]=list(dict.fromkeys(values))[:12]
                    results.append({'id':synset,'lemma':label,'part_of_speech':POS.get(sense.get('partOfSpeech'),'word'),
                        'definitions':sense.get('definition',[]),'examples':[text for item in sense.get('example',[])[:3] if (text:=example_text(item))],
                        'synonyms':[w for w in sense.get('members',[]) if normalize(w)!=lemma],
                        'antonyms':list(dict.fromkeys(opposites)),'related':related})
                    if len(results)>=20:break
                if len(results)>=20:break
    fallback=system_definition(word) if not results else ''
    return {'query':word,'found':bool(results or fallback),'source':EDITION if results else 'System WordNet' if fallback else None,
        'source_url':SOURCE if results else None,'attribution':ATTRIBUTION if results else None,
        'results':results,'system_text':fallback,'hint':'' if results or fallback else 'No entry found. lk words setup installs the portable dictionary; spelling and personal words are separate.'}


# A readable learning selection avoids abbreviations and specialist taxonomic names.
LAUNCH_WORDS=('serendipity','pellucid','susurrus','perspicacious','obdurate','halcyon',
              'sagacious','lucent','taciturn','ebullient','equanimity','resplendent',
              'ephemeral','ineffable','palimpsest','sanguine','laconic','verdant',
              'mellifluous','liminal','luminous','quixotic','redolent','assiduous',
              'insouciant','numinous','salubrious','tenacious','mercurial','capacious')


def launch_word():
    """A real local entry from a shuffled learning pool; never download data."""
    with connection() as db:
        if db is None:return None
        placeholders=','.join('?' for _ in LAUNCH_WORDS)
        candidates=[r[0] for r in db.execute('SELECT DISTINCT word FROM senses WHERE word IN ('+placeholders+')',LAUNCH_WORDS)]
    if not candidates:return None
    selected=secrets.choice(candidates)
    try:
        with (root()/'launch-word.lock').open('a') as lock:
            fcntl.flock(lock,fcntl.LOCK_EX)
            try:state=json.loads((root()/'launch-word.json').read_text())
            except (OSError,ValueError):state={}
            if not isinstance(state,dict):state={}
            last=state.get('word');remaining=state.get('remaining',[])
            if not isinstance(remaining,list):remaining=[]
            pool=list(dict.fromkeys(word for word in remaining if isinstance(word,str) and word in candidates)) or candidates[:]
            selected=secrets.choice([word for word in pool if word!=last] or pool)
            pool.remove(selected)
            import book_reader
            book_reader.write_json(root()/'launch-word.json',{'word':selected,'remaining':pool})
    except OSError:pass  # A read-only reference can still offer a launch word.
    value=lookup(selected)
    for sense in value['results']:
        if sense['definitions']:
            return {'word':sense['lemma'],'definition':sense['definitions'][0],
                    'part_of_speech':sense['part_of_speech'],'source':value['source']}
    return None


def system_wordlists():return [Path('/usr/share/dict/words'),Path('/usr/share/dict/american-english'),Path('/usr/share/dict/british-english')]


def personal_words():
    try:return {normalize(w):w for w in personal_path().read_text().splitlines() if w.strip()}
    except FileNotFoundError:return {}


def add_personal(word):
    word=query_text(word)
    if any(c.isspace() for c in word):raise ValueError('Add one word at a time')
    values=personal_words();values[normalize(word)]=word
    path=personal_path();path.parent.mkdir(parents=True,exist_ok=True)
    temporary=path.with_suffix('.tmp');temporary.write_text('\n'.join(values[k] for k in sorted(values))+'\n');os.replace(temporary,path)
    return {'added':word,'source':'Personal vocabulary'}


def system_checks(tokens,language):
    if not tokens:return {}
    for name,args in [('hunspell',['-d',language,'-a']),('aspell',['--lang='+language,'-a'])]:
        executable=shutil.which(name)
        if not executable:continue
        try:result=subprocess.run([executable,*args],input=''.join('^'+word+'\n' for word in tokens),capture_output=True,text=True,timeout=3)
        except (OSError,subprocess.TimeoutExpired):continue
        if result.returncode:continue
        groups=[group.strip().splitlines() for group in result.stdout.partition('\n')[2].split('\n\n') if group.strip()]
        if len(groups)!=len(tokens):continue
        rows={}
        for word,lines in zip(tokens,groups):
            if len(lines)!=1:continue
            line=lines[0]
            if line[0] in '*+-':rows[word]=(True,[],name+' '+language)
            elif line[0] in '&#':rows[word]=(False,line.split(': ',1)[1].split(', ')[:8] if ': ' in line else [],name+' '+language)
        return rows
    return {}


@functools.lru_cache(maxsize=2)
def portable_spelling(language):
    package=root()/'spylls-0.1.7'
    if not package.is_dir():return None
    if str(package) not in sys.path:sys.path.insert(0,str(package))
    from spylls.hunspell import Dictionary
    # Prefer an installed matching-language dictionary; never use US rules for GB.
    for base in [Path.home()/'Library/Spelling',Path('/Library/Spelling'),Path('/usr/share/hunspell'),Path('/usr/share/myspell/dicts')]:
        if (base/(language+'.aff')).is_file() and (base/(language+'.dic')).is_file():
            return Dictionary.from_files(str(base/language)),'System Hunspell dictionary '+language
    if language=='en_US':return Dictionary.from_files(str(package/'spylls/hunspell/data/en/en_US')),'SCOWL en_US · Spylls 0.1.7'
    return None


def spell(text,language='en_US'):
    text=query_text(text,MAX_TEXT_CHARS)
    if language not in {'en_US','en_GB'}:raise ValueError('Choose en_US or en_GB spelling')
    tokens=list(dict.fromkeys(re.findall(r"[^\W\d_]+(?:['’][^\W\d_]+)*",text,re.UNICODE)))
    if len(tokens)>MAX_CHECK_WORDS:raise ValueError('Check at most '+str(MAX_CHECK_WORDS)+' distinct words at a time')
    personal=personal_words();rows=[]
    portable=portable_spelling(language)
    system=system_checks(tokens,language)
    lists={}
    for path in system_wordlists():
        if path.is_file():
            with path.open(errors='replace') as stream:
                for i,line in enumerate(stream):
                    if i>=500000:break
                    value=line.strip()
                    if value:lists[normalize(value)]=value
    with connection() as db:
        for word in tokens:
            key=normalize(word)
            if key in personal:rows.append({'word':word,'recognized':True,'suggestions':[],'source':'Personal vocabulary'});continue
            recognized,suggestions,source=system.get(word,(None,[],''))
            if recognized is None and portable and len(word)<=50:
                recognized=bool(portable[0].lookup(word));source=portable[1]
            if recognized is None or recognized is False:
                present=bool(db and db.execute('SELECT 1 FROM vocabulary WHERE word=?',(key,)).fetchone())
                if recognized is None:
                    recognized=True if present or key in lists else None
                    source=EDITION if present else 'System word list' if key in lists else 'Vocabulary lookup only'
                if recognized is not True and not suggestions:
                    candidates=[r[0] for r in db.execute('SELECT word FROM vocabulary WHERE word>=? AND word<? AND length(word) BETWEEN ? AND ? LIMIT 5000',(key[:1],key[:1]+'\uffff',max(1,len(key)-2),len(key)+2))] if db else []
                    candidates+=list(k for k in lists if k.startswith(key[:1]) and abs(len(k)-len(key))<=2)[:5000]
                    suggestions=difflib.get_close_matches(key,sorted(set(candidates)),n=8,cutoff=.7)
            rows.append({'word':word,'recognized':recognized,'suggestions':suggestions,'source':source})
    return {'language':language,'words':rows,'note':'Unrecognized vocabulary is not proof of a spelling error. The portable baseline includes US spelling. Installed Hunspell/Aspell dictionaries take priority; GB spelling needs a matching system dictionary.'}


def find(pattern,limit=40):
    pattern=normalize(query_text(pattern));limit=max(1,min(100,int(limit)))
    # Escape SQL wildcards; only shell-style * and ? have pattern meaning here.
    sql=pattern.replace('\\','\\\\').replace('%','\\%').replace('_','\\_').replace('*','%').replace('?','_')
    matches=[];source=None
    with connection() as db:
        if db:
            source=EDITION
            matches=[r[0] for r in db.execute("SELECT label FROM vocabulary WHERE word LIKE ? ESCAPE '\\' ORDER BY word LIMIT ?",(sql,limit))]
    if not matches:
        for path in system_wordlists():
            if not path.is_file():continue
            with path.open(errors='replace') as stream:
                for i,line in enumerate(stream):
                    if i>=500000:break
                    if fnmatch.fnmatchcase(normalize(line),pattern):matches.append(line.strip());source='System word list · '+str(path)
                    if len(matches)>=limit:break
            if len(matches)>=limit:break
    return {'pattern':pattern,'matches':matches,'limit':limit,'source':source}


def tool(action,query,language='en_US'):
    if action=='lookup':return lookup(query)
    if action=='spell':return spell(query,language)
    if action=='find':return find(query)
    if action=='status':return status()
    raise ValueError('Choose lookup, spell, find or status')


def display(value):
    if 'results' in value:
        lines=[value['query'].upper()+' · '+(value['source'] or 'No entry')]
        for i,row in enumerate(value['results'],1):
            lines.append(f"{i}. {row['lemma']} · {row['part_of_speech']}")
            lines += ['   '+v for v in row['definitions']]
            lines += ['   Example: '+v for v in row['examples']]
            for field in ('synonyms','antonyms'):
                if row[field]:lines.append('   '+field.title()+': '+', '.join(row[field]))
            for field,words in row['related'].items():lines.append('   '+{'hypernym':'Broader','hyponym':'More specific','similar':'Similar'}[field]+': '+', '.join(words))
        if value['system_text']:lines.append(value['system_text'])
        if value.get('hint'):lines.append(value['hint'])
        if value.get('attribution'):lines+=['',value['attribution'],SOURCE]
        return '\n'.join(lines)
    if 'words' in value:
        return '\n'.join([f"{r['word']} · "+('recognized' if r['recognized'] is True else 'check spelling' if r['recognized'] is False else 'not in available vocabulary')+(' · '+', '.join(r['suggestions']) if r['suggestions'] else '')+' · '+r['source'] for r in value['words']]+['',value['note']])
    if 'matches' in value:return '\n'.join(value['matches']) or 'No matching words in available local dictionaries.'
    return json.dumps(value,ensure_ascii=False,indent=2)


def main(argv=None,ui=None):
    parser=argparse.ArgumentParser(prog='lk words',description=__doc__)
    parser.add_argument('action',nargs='?',default='desk',choices=['desk','status','setup','lookup','spell','find','add'])
    parser.add_argument('--node',help='Use an explicitly chosen paired Fabric node');parser.add_argument('text',nargs='*');parser.add_argument('--language',choices=['en_US','en_GB'],default='en_US');parser.add_argument('--json',action='store_true')
    args=parser.parse_args(argv)
    try:
        if not args.json and ui and sys.stdin.isatty() and sys.stdout.isatty() and args.action in {'desk','lookup','spell','find'}:
            import words_desk
            return words_desk.desk(ui,node=args.node,language=args.language,initial=' '.join(args.text),view={'spell':3,'find':4}.get(args.action,0))
        if args.action=='desk':args.action='status'
        if args.node:
            if args.action=='add':raise ValueError('Personal words are local; add them on the intended computer')
            import fabric_files
            value=fabric_files.request('/v1/words',{'target':args.node},json.dumps({'action':args.action,'query':' '.join(args.text),'language':args.language,'confirm':args.action=='setup'}).encode(),timeout=60)
        elif args.action=='setup':
            if not args.json:print('Installing offline English reference · about 12 MB download · no AI runtime required',file=sys.stderr)
            value=setup()
        elif args.action=='add':value=add_personal(' '.join(args.text))
        else:value=tool(args.action,' '.join(args.text),args.language)
        text=json.dumps(value,ensure_ascii=False,indent=2) if args.json else display(value)
        print(text)
        return 0
    except (OSError,ValueError,RuntimeError,sqlite3.Error,zipfile.BadZipFile,subprocess.SubprocessError) as exc:
        print('LOOK Words: '+str(exc),file=sys.stderr);return 1
