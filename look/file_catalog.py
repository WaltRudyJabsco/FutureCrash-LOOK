"""LOOK local file catalog: cheap metadata first, content understanding later."""
from __future__ import annotations
import os, sqlite3, time, re, contextlib, subprocess, shutil, zipfile, html.parser
import fcntl
from pathlib import Path

SCHEMA_VERSION=2
CONTENT_MAX_FILE_BYTES=4*1024*1024
CONTENT_MAX_CHARS=256*1024
CONTENT_EXTS={'.txt','.md','.markdown','.py','.js','.ts','.tsx','.jsx','.css','.json','.yaml','.yml','.toml','.ini','.cfg','.sh','.zsh','.html','.htm','.docx','.pdf','.epub'}
SKIP_NAMES={'.git','.svn','.hg','node_modules','__pycache__','.cache','Caches','cache','.Trash','.npm','.cargo','target','DerivedData'}
SKIP_PREFIXES=('/proc','/sys','/dev','/run','/private/var/folders')
TYPE_WORDS={'pdf':'.pdf','zip':'.zip','python':'.py','markdown':'.md','text':'.txt','document':None,'image':None,'audio':None,'video':None}
GROUP_EXTS={
 'document':{'.pdf','.doc','.docx','.odt','.rtf','.txt','.md','.pages'},
 'image':{'.jpg','.jpeg','.png','.gif','.webp','.heic','.tif','.tiff','.svg'},
 'audio':{'.mp3','.m4a','.aac','.flac','.wav','.ogg','.opus'},
 'video':{'.mp4','.m4v','.mov','.mkv','.webm','.avi'},
}

def connect(path):
    path=Path(path); path.parent.mkdir(parents=True,exist_ok=True)
    # Catalog readers should tolerate a scanner holding SQLite's writer lock.
    db=sqlite3.connect(path, timeout=30.0)
    db.execute('PRAGMA busy_timeout=30000')
    db.execute('PRAGMA journal_mode=WAL'); db.execute('PRAGMA synchronous=NORMAL')
    db.execute('''CREATE TABLE IF NOT EXISTS files(
      path TEXT PRIMARY KEY, root TEXT NOT NULL, name TEXT NOT NULL, ext TEXT NOT NULL,
      bytes INTEGER NOT NULL, mtime REAL NOT NULL, inode INTEGER, mode INTEGER, scanned REAL NOT NULL)''')
    db.execute('CREATE INDEX IF NOT EXISTS files_name ON files(name COLLATE NOCASE)')
    db.execute('CREATE INDEX IF NOT EXISTS files_ext ON files(ext)')
    db.execute('CREATE INDEX IF NOT EXISTS files_mtime ON files(mtime DESC)')
    db.execute('CREATE INDEX IF NOT EXISTS files_root ON files(root)')
    db.execute('CREATE TABLE IF NOT EXISTS roots(root TEXT PRIMARY KEY, scanned REAL NOT NULL, count INTEGER NOT NULL)')
    db.execute("CREATE TABLE IF NOT EXISTS content_state(path TEXT PRIMARY KEY, mtime REAL NOT NULL, bytes INTEGER NOT NULL, kind TEXT NOT NULL, chars INTEGER NOT NULL, indexed REAL NOT NULL, error TEXT NOT NULL DEFAULT '')")
    try:
        db.execute("CREATE VIRTUAL TABLE IF NOT EXISTS content_fts USING fts5(path UNINDEXED, body, tokenize='unicode61')")
    except sqlite3.OperationalError:
        pass
    # user_version is a migration marker, not connection setup. Writing it on
    # every open creates needless writer contention with background scans.
    current=int(db.execute('PRAGMA user_version').fetchone()[0])
    if current < SCHEMA_VERSION:
        db.execute(f'PRAGMA user_version={SCHEMA_VERSION}')
        db.commit()
    return db

def _skip_dir(path,name,default_home=False):
    s=str(path)
    if any(s==p or s.startswith(p+'/') for p in SKIP_PREFIXES): return True
    if name in SKIP_NAMES: return True
    if default_home and name.startswith('.'): return True
    return False

class _HTMLText(html.parser.HTMLParser):
    def __init__(self): super().__init__(); self.parts=[]; self.skip=0
    def handle_starttag(self,tag,attrs):
        if tag in {"script","style","noscript"}: self.skip+=1
    def handle_endtag(self,tag):
        if tag in {"script","style","noscript"} and self.skip: self.skip-=1
    def handle_data(self,data):
        if not self.skip and data.strip(): self.parts.append(data)

def _html_text(raw):
    parser=_HTMLText(); parser.feed(raw); return "\n".join(parser.parts)

def _extract_text(path,ext):
    """Cheap deterministic extraction only. Never OCR and never invoke a model."""
    try:
        if ext in {'.txt','.md','.markdown','.py','.js','.ts','.tsx','.jsx','.css','.json','.yaml','.yml','.toml','.ini','.cfg','.sh','.zsh'}:
            text=path.read_text(encoding='utf-8',errors='replace')
        elif ext in {'.html','.htm'}:
            text=_html_text(path.read_text(encoding='utf-8',errors='replace'))
        elif ext=='.docx':
            import xml.etree.ElementTree as ET
            with zipfile.ZipFile(path) as z: raw=z.read('word/document.xml')
            root=ET.fromstring(raw); ns='{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'
            text='\n'.join(''.join(n.text or '' for n in para.iter(ns+'t')) for para in root.iter(ns+'p'))
        elif ext=='.epub':
            parts=[]
            with zipfile.ZipFile(path) as z:
                for name in sorted(z.namelist()):
                    if name.casefold().endswith(('.xhtml','.html','.htm')):
                        parts.append(_html_text(z.read(name).decode('utf-8','replace')))
            text='\n'.join(parts)
        elif ext=='.pdf':
            exe=shutil.which('pdftotext')
            if not exe: return None,'pdftotext unavailable'
            run=subprocess.run([exe,'-q',str(path),'-'],capture_output=True,text=True,timeout=12)
            if run.returncode: return None,'pdftotext failed'
            text=run.stdout
        else: return None,'unsupported'
        text='\n'.join(line.rstrip() for line in text.replace('\x00',' ').splitlines()).strip()
        return text[:CONTENT_MAX_CHARS],''
    except Exception as exc:
        return None,str(exc)[:160]

def _index_content(db,path,ext,size,mtime,stamp):
    if ext not in CONTENT_EXTS or size>CONTENT_MAX_FILE_BYTES: return False
    old=db.execute('SELECT mtime,bytes FROM content_state WHERE path=?',(str(path),)).fetchone()
    if old and float(old[0])==float(mtime) and int(old[1])==int(size): return False
    text,error=_extract_text(path,ext)
    try: db.execute('DELETE FROM content_fts WHERE path=?',(str(path),))
    except sqlite3.OperationalError: return False
    if text: db.execute('INSERT INTO content_fts(path,body) VALUES(?,?)',(str(path),text))
    db.execute('INSERT OR REPLACE INTO content_state(path,mtime,bytes,kind,chars,indexed,error) VALUES(?,?,?,?,?,?,?)',(str(path),mtime,size,ext,len(text or ''),stamp,error))
    return bool(text)

@contextlib.contextmanager
def _scan_lock(db_path):
    """One crawler per catalog; readers remain free under SQLite WAL."""
    lock_path=Path(str(db_path)+'.scan.lock')
    lock_path.parent.mkdir(parents=True,exist_ok=True)
    handle=open(lock_path,'a+')
    try:
        try:
            fcntl.flock(handle.fileno(),fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:
            yield False
            return
        yield True
    finally:
        try: fcntl.flock(handle.fileno(),fcntl.LOCK_UN)
        except OSError: pass
        handle.close()

def scan(db_path,root=None,default_home=False):
    base=Path(root or Path.home()).expanduser().resolve()
    if not base.is_dir(): raise NotADirectoryError(base)
    with _scan_lock(db_path) as acquired:
        if not acquired:
            return {'root':str(base),'count':0,'skipped':0,'seconds':0.0,'busy':True}
        return _scan_locked(db_path,base,default_home)

def _scan_locked(db_path,base,default_home=False):
    db=connect(db_path); started=time.monotonic(); stamp=time.time(); count=0; skipped=0; content_indexed=0
    batch=[]
    for dirpath,dirnames,filenames in os.walk(base,followlinks=False):
        here=Path(dirpath)
        kept=[]
        for d in dirnames:
            if _skip_dir(here/d,d,default_home): skipped+=1
            else: kept.append(d)
        dirnames[:]=kept
        for name in filenames:
            if default_home and name.startswith('.'): continue
            p=here/name
            try:
                st=p.stat()
                if not p.is_file(): continue
            except (OSError,PermissionError): skipped+=1; continue
            ext=p.suffix.casefold(); size=int(st.st_size); mtime=float(st.st_mtime)
            batch.append((str(p),str(base),name,ext,size,mtime,int(st.st_ino),int(st.st_mode),stamp)); count+=1
            if _index_content(db,p,ext,size,mtime,stamp): content_indexed+=1
            if len(batch)>=1000:
                db.executemany('INSERT OR REPLACE INTO files VALUES(?,?,?,?,?,?,?,?,?)',batch); batch.clear()
    if batch: db.executemany('INSERT OR REPLACE INTO files VALUES(?,?,?,?,?,?,?,?,?)',batch)
    # Anything from an older scan of this exact root disappeared.
    stale=[r[0] for r in db.execute('SELECT path FROM files WHERE root=? AND scanned<?',(str(base),stamp))]
    for old_path in stale:
        try: db.execute('DELETE FROM content_fts WHERE path=?',(old_path,))
        except sqlite3.OperationalError: pass
        db.execute('DELETE FROM content_state WHERE path=?',(old_path,))
    db.execute('DELETE FROM files WHERE root=? AND scanned<?',(str(base),stamp))
    db.execute('INSERT OR REPLACE INTO roots VALUES(?,?,?)',(str(base),stamp,count)); db.commit(); db.close()
    return {'root':str(base),'count':count,'skipped':skipped,'content_indexed':content_indexed,'seconds':time.monotonic()-started}

def _terms(query):
    return re.findall(r'[\w.+-]+',query.casefold())

def search(db_path,query,limit=80):
    db=connect(db_path); terms=_terms(query); now=time.time(); where=[]; params=[]; extset=None
    # Cheap natural-language intent extraction. Remaining words become filename/path terms.
    remaining=[]
    for t in terms:
        if t in TYPE_WORDS:
            ext=TYPE_WORDS[t]
            extset={ext} if ext else GROUP_EXTS.get(t)
        elif t in {'file','files','find','show','me','the','a','an','my','that','named','called','about'}: pass
        elif t in {'today','yesterday','recent','recently'}: pass
        else: remaining.append(t)
    if 'today' in terms: where.append('mtime>=?'); params.append(now-86400)
    elif 'yesterday' in terms: where.append('mtime>=?'); params.append(now-172800)
    elif 'recent' in terms or 'recently' in terms: where.append('mtime>=?'); params.append(now-14*86400)
    if extset:
        qs=','.join('?' for _ in extset); where.append(f'ext IN ({qs})'); params.extend(sorted(extset))
    for t in remaining:
        where.append('(name LIKE ? OR path LIKE ?)'); like=f'%{t}%'; params.extend((like,like))
    sql='SELECT path,name,ext,bytes,mtime,root FROM files'
    if where: sql+=' WHERE '+' AND '.join(where)
    order='bytes DESC' if any(x in terms for x in ('big','biggest','large','largest')) else 'mtime DESC'
    sql+=f' ORDER BY {order} LIMIT ?'; params.append(int(limit))
    rows=[dict(zip(('path','name','ext','bytes','mtime','root'),r)) for r in db.execute(sql,params)]
    db.close(); return rows

def content_search(db_path,query,limit=80):
    db=connect(db_path); terms=_terms(query)
    stop={'where','was','that','thing','i','wrote','write','about','find','show','me','the','a','an','my','file','files','document','documents','something','with','of','to','in','on','for','and','or','is','it'}
    words=[t for t in terms if t not in stop and t not in TYPE_WORDS and len(t)>1]
    if not words: db.close(); return []
    fts=' OR '.join('"'+w.replace('"','')+'"' for w in words[:16])
    try:
        ext_filter=next((TYPE_WORDS[t] for t in terms if t in TYPE_WORDS and TYPE_WORDS[t]),None)
        sql="SELECT f.path,fi.name,fi.ext,fi.bytes,fi.mtime,fi.root,bm25(content_fts),snippet(content_fts,1,'[',']',' … ',18) FROM content_fts f JOIN files fi ON fi.path=f.path WHERE content_fts MATCH ?"
        params=[fts]
        if ext_filter: sql+=" AND fi.ext=?"; params.append(ext_filter)
        sql+=" ORDER BY bm25(content_fts) LIMIT ?"; params.append(int(limit))
        rows=[dict(zip(('path','name','ext','bytes','mtime','root','rank','snippet'),r),match='content') for r in db.execute(sql,params)]
    except sqlite3.OperationalError: rows=[]
    db.close(); return rows

def combined_search(db_path,query,limit=80):
    meta=search(db_path,query,limit); content=content_search(db_path,query,limit); merged={}
    for row in content: merged[row['path']]=row
    for row in meta:
        if row['path'] in merged: merged[row['path']]['match']='name+content'
        else: row=dict(row); row['match']='name'; merged[row['path']]=row
    def score(row):
        return (0,float(row.get('rank') or 0),-float(row.get('mtime') or 0)) if 'rank' in row else (1,0,-float(row.get('mtime') or 0))
    return sorted(merged.values(),key=score)[:int(limit)]

def status(db_path):
    db=connect(db_path)
    total=db.execute('SELECT COUNT(*) FROM files').fetchone()[0]
    content=db.execute('SELECT COUNT(*) FROM content_state WHERE chars>0').fetchone()[0]
    roots=[{'root':r,'scanned':s,'count':c} for r,s,c in db.execute('SELECT root,scanned,count FROM roots ORDER BY root')]
    db.close(); return {'count':total,'content_count':content,'roots':roots}

def search_rows(rows,query,limit=80):
    terms=_terms(query); now=time.time(); extset=None; remaining=[]
    for t in terms:
        if t in TYPE_WORDS:
            ext=TYPE_WORDS[t]; extset={ext} if ext else GROUP_EXTS.get(t)
        elif t in {'file','files','find','show','me','the','a','an','my','that','named','called','about'}: pass
        elif t in {'today','yesterday','recent','recently','big','biggest','large','largest'}: pass
        else: remaining.append(t)
    out=[]
    for row in rows:
        ext=str(row.get('ext') or '').casefold(); mtime=float(row.get('mtime') or 0)
        if extset and ext not in extset: continue
        if 'today' in terms and mtime<now-86400: continue
        if 'yesterday' in terms and mtime<now-172800: continue
        if ('recent' in terms or 'recently' in terms) and mtime<now-14*86400: continue
        hay=(str(row.get('name') or '')+' '+str(row.get('path') or '')).casefold()
        if all(t in hay for t in remaining): out.append(dict(row))
    key=(lambda r:int(r.get('bytes') or 0)) if any(x in terms for x in ('big','biggest','large','largest')) else (lambda r:float(r.get('mtime') or 0))
    return sorted(out,key=key,reverse=True)[:int(limit)]
