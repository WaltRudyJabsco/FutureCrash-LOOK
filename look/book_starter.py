"""Opt-in daily starter refill using public-domain EPUBs from a bulk mirror."""
import csv,fcntl,gzip,json,os,re,subprocess,sys,time,urllib.request,zipfile
from pathlib import Path
import book_core
DAY=24*3600
MIRROR='https://gutenberg.pglaf.org/cache/epub'
MAX_BYTES=50*1024*1024
MAX_UNPACKED_BYTES=250*1024*1024
MAX_FAILURES_PER_RUN=30
DOWNLOAD_DELAY_SECONDS=2
DOWNLOAD_DEADLINE_SECONDS=90

def folder():return Path.home()/'.local/share/look/gutenberg-starter'

def configure(shelf,enabled,target=1000):
    if type(enabled) is not bool or type(target) is not int or not 1<=target<=10000:raise ValueError('Choose enabled true/false and a target from 1 to 10000')
    with shelf.edit() as data:
        data['refill']=dict(data.get('refill',{}),enabled=enabled,target=target)
    return data['refill']

def plan():
    root=folder();root.mkdir(parents=True,exist_ok=True)
    manifest=root/'manifest.json'
    if manifest.exists():return json.loads(manifest.read_text()).get('candidates',[])
    catalog=root/'catalog.csv.gz'
    if not catalog.exists():
        with urllib.request.urlopen('https://www.gutenberg.org/cache/epub/feeds/pg_catalog.csv.gz',timeout=45) as response:
            raw=response.read(32*1024*1024+1)
        if len(raw)>32*1024*1024:raise ValueError('Catalog exceeds size limit')
        temp=catalog.with_suffix('.tmp');temp.write_bytes(raw);temp.replace(catalog)
    rows=[];seen=set()
    with gzip.open(catalog,'rt',encoding='utf-8-sig') as stream:
        for row in csv.DictReader(stream):
            if row['Type']!='Text' or row['Language']!='en':continue
            title=row['Title'];author=row['Authors'].split(';')[0]
            key=(re.sub(r'\W+',' ',title.casefold()).strip(),author.casefold())
            if key in seen or re.search(r'\b(magazine|periodical|catalogue|bulletin)\b',title,re.I):continue
            seen.add(key);rows.append({'id':row['Text#'],'title':title,'author':author})
    return rows

def fetch(shelf,row):
    ident=str(row['id'])
    if not re.fullmatch(r'[1-9][0-9]{0,8}',ident):raise ValueError('Invalid Gutenberg ID')
    destination=shelf.root/'Gutenberg Starter 1000';destination.mkdir(exist_ok=True)
    target=destination/('pg'+ident+'.epub')
    if target.exists():
        book_core.metadata(target);return target
    for variant in ('images','noimages'):
        part=destination/('.pg'+ident+'.part')
        try:
            time.sleep(DOWNLOAD_DELAY_SECONDS)
            with urllib.request.urlopen(f'{MIRROR}/{ident}/pg{ident}-{variant}.epub',timeout=30) as response,part.open('wb') as out:
                size=0;deadline=time.monotonic()+DOWNLOAD_DEADLINE_SECONDS
                while block:=response.read(65536):
                    size+=len(block)
                    if size>MAX_BYTES or time.monotonic()>deadline:raise ValueError('EPUB exceeds download budget')
                    out.write(block)
            with zipfile.ZipFile(part) as archive:
                def read(name):
                    info=archive.getinfo(name)
                    if info.file_size>book_core.MAX_METADATA_BYTES:raise ValueError('EPUB metadata exceeds size limit')
                    return archive.read(info)
                if sum(info.file_size for info in archive.infolist())>MAX_UNPACKED_BYTES:raise ValueError('EPUB expands beyond size limit')
                container=book_core.xml(read('META-INF/container.xml'))
                name=next(n.get('full-path') for n in container.iter() if n.tag.endswith('rootfile'))
                opf=book_core.xml(read(name))
                rights=' '.join(''.join(n.itertext()) for n in opf.iter() if n.tag.endswith('}rights'))
                if 'public domain' not in rights.casefold():raise ValueError('No public-domain declaration')
                if archive.testzip():raise ValueError('EPUB checksum failed')
            shelf.publish(part,target);book_core.metadata(target);return target
        except Exception as exc:error=exc
        finally:part.unlink(missing_ok=True)
    raise ValueError(str(error))

def pool_count(data):
    # Favorites stay on disk but no longer occupy a discovery slot. Pending
    # removals count until expiry so the existing 48-hour grace stays intact.
    return sum(not r.get('favorite') for r in data['entries'])

def run(shelf=None):
    shelf=shelf or book_core.Shelf()
    root=folder();root.mkdir(parents=True,exist_ok=True)
    with (root/'refill.lock').open('a') as lock:
        try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:return {'state':'running'}
        if not shelf.root.is_dir():return {'state':'offline'}
        removed=shelf.purge_rejected();settings=shelf.load().get('refill',{})
        if not settings.get('enabled'):return {'state':'disabled','removed':removed}
        with shelf.edit() as data:data['refill'].update(last_attempt=time.time(),state='running',added=0,error='')
        added=0;errors=[];failure=''
        try:
            if pool_count(shelf.load())>=settings.get('target',1000):return {'state':'complete','added':0,'removed':removed}
            for row in plan():
                data=shelf.load();settings=data.get('refill',{})
                if not settings.get('enabled') or pool_count(data)>=settings.get('target',1000):break
                ident=str(row['id'])
                known={book_core.gutenberg_id(r) for r in data['entries']}
                if ident in known or ident in data.get('rejected_gutenberg',{}):continue
                # Exact ID exclusions survive deletion; title/author comparison
                # also avoids obvious duplicate editions already on the shelf.
                normalize=lambda x:re.sub(r'\W+',' ',str(x).casefold()).strip()
                if any(normalize(r['title'])==normalize(row['title']) and normalize(r.get('author'))==normalize(row.get('author')) for r in data['entries']):continue
                try:path=fetch(shelf,row)
                except (OSError,ValueError,zipfile.BadZipFile) as exc:
                    errors.append({'id':ident,'error':str(exc)})
                    if len(errors)>=MAX_FAILURES_PER_RUN:break
                    continue
                shelf.scan()
                with shelf.edit() as current:
                    for entry in current['entries']:
                        if entry['path']==str(path):entry.update(gutenberg_id=ident,source_url='https://www.gutenberg.org/ebooks/'+ident,starter_managed=True)
                    added+=1;current['refill']['added']=added
            return {'state':'complete' if pool_count(shelf.load())>=settings.get('target',1000) else 'partial','added':added,'removed':removed,'errors':errors}
        except Exception as exc:
            failure=str(exc);raise
        finally:
            with shelf.edit() as data:data['refill'].update(state='failed' if failure else 'idle',error=failure,last_run=time.time(),added=added,errors=errors[-5:])

def tick():
    shelf=book_core.Shelf()
    if not shelf.root.is_dir():return
    shelf.purge_rejected()
    settings=shelf.load().get('refill',{})
    if not settings.get('enabled') or time.time()-settings.get('last_attempt',0)<DAY:return
    with shelf.edit() as data:data['refill']['last_attempt']=time.time()
    subprocess.Popen([sys.executable,str(Path(__file__).resolve())],stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,start_new_session=True)

if __name__=='__main__':print(json.dumps(run()))
