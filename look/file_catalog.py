"""LOOK local file catalog: cheap metadata first, content understanding later."""
from __future__ import annotations
import os, sqlite3, time, re, contextlib
import fcntl
from pathlib import Path

SCHEMA_VERSION=1
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
    db=connect(db_path); started=time.monotonic(); stamp=time.time(); count=0; skipped=0
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
            batch.append((str(p),str(base),name,p.suffix.casefold(),int(st.st_size),float(st.st_mtime),int(st.st_ino),int(st.st_mode),stamp)); count+=1
            if len(batch)>=1000:
                db.executemany('INSERT OR REPLACE INTO files VALUES(?,?,?,?,?,?,?,?,?)',batch); batch.clear()
    if batch: db.executemany('INSERT OR REPLACE INTO files VALUES(?,?,?,?,?,?,?,?,?)',batch)
    # Anything from an older scan of this exact root disappeared.
    db.execute('DELETE FROM files WHERE root=? AND scanned<?',(str(base),stamp))
    db.execute('INSERT OR REPLACE INTO roots VALUES(?,?,?)',(str(base),stamp,count)); db.commit(); db.close()
    return {'root':str(base),'count':count,'skipped':skipped,'seconds':time.monotonic()-started}

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


def resolve_paths(db_path, query, kind=None, limit=8):
    """Resolve a human phrase to local catalog paths without making CLI grammar fuzzy.

    Directories are inferred from indexed file parents, so the metadata schema stays
    cheap and unchanged.  This is a resolver, not a launcher: callers decide whether
    an ambiguous result is safe to act on.
    """
    terms=_terms(query)
    folder_words={'folder','directory','dir'}
    file_words={'file'}
    requested_kind=kind
    if requested_kind is None:
        if any(t in folder_words for t in terms): requested_kind='directory'
        elif any(t in file_words for t in terms): requested_kind='file'
    noise=folder_words|file_words|{'open','preview','reveal','show','me','the','a','an','my','named','called'}
    wanted=[t for t in terms if t not in noise]
    if not wanted: return []

    db=connect(db_path)
    # Pull a bounded candidate set with SQL doing the coarse lexical filtering.
    where=[]; params=[]
    for t in wanted:
        like=f'%{t}%'; where.append('(name LIKE ? OR path LIKE ?)'); params.extend((like,like))
    sql='SELECT path,name,mtime FROM files WHERE '+' AND '.join(where)+' ORDER BY mtime DESC LIMIT 400'
    rows=list(db.execute(sql,params)); roots=list(db.execute('SELECT root,scanned FROM roots'))
    db.close()

    candidates={}
    def add(path, candidate_kind, mtime):
        if requested_kind and candidate_kind!=requested_kind: return
        p=Path(path); hay=str(p).casefold(); name=p.name.casefold()
        if not all(t in hay for t in wanted): return
        # Exact basename is strongest, then basename containing all terms, then path.
        joined=' '.join(wanted)
        score=1000 if name==joined else 200 if all(t in name for t in wanted) else 100
        if score<1000: score-=max(0,len(p.parts)-3) * 0.01
        old=candidates.get(str(p))
        item={'path':str(p),'kind':candidate_kind,'mtime':float(mtime or 0),'score':score}
        if old is None or (item['score'],item['mtime'])>(old['score'],old['mtime']): candidates[str(p)]=item

    for path,name,mtime in rows:
        add(path,'file',mtime)
        parent=Path(path).parent
        # Every parent represented by an indexed file is known to have existed at scan time.
        while parent != parent.parent:
            if all(t in str(parent).casefold() for t in wanted): add(parent,'directory',mtime)
            parent=parent.parent
    for root_path,scanned in roots: add(root_path,'directory',scanned)
    return sorted(candidates.values(),key=lambda r:(r['score'],r['mtime']),reverse=True)[:int(limit)]

def status(db_path):
    db=connect(db_path)
    total=db.execute('SELECT COUNT(*) FROM files').fetchone()[0]
    roots=[{'root':r,'scanned':s,'count':c} for r,s,c in db.execute('SELECT root,scanned,count FROM roots ORDER BY root')]
    db.close(); return {'count':total,'roots':roots}

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
