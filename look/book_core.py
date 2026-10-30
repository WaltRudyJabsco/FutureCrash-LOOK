"""Bookshelf ownership and bounded document metadata; never launches a reader."""
from __future__ import annotations
import contextlib
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
import zipfile

FORMATS={'.epub','.pdf'}
STATUSES=('To Read','Reading','Finished')
MAX_METADATA_BYTES=2*1024*1024
MAX_DOWNLOAD_BYTES=100*1024*1024
MAX_SCAN_FILES=10000
GUTENBERG='https://www.gutenberg.org/ebooks/search.opds/'


def clean(value):return ''.join(c for c in str(value or '') if c.isprintable()).strip()


def xml(data):
    if len(data)>MAX_METADATA_BYTES or b'<!DOCTYPE' in data.upper() or b'<!ENTITY' in data.upper():
        raise ValueError('Document metadata is too large or contains entities')
    try:return ET.fromstring(data)
    except ET.ParseError as exc:raise ValueError("Invalid document metadata XML") from exc


def _metadata(path):
    path=Path(path);result={'title':clean(path.stem),'author':'','format':path.suffix[1:].upper()}
    if path.suffix.casefold()=='.epub':
        with zipfile.ZipFile(path) as archive:
            def read(name):
                info=archive.getinfo(name)
                if info.file_size>MAX_METADATA_BYTES:raise ValueError('EPUB metadata exceeds size limit')
                return archive.read(info)
            container=xml(read('META-INF/container.xml'))
            package=next((n.get('full-path') for n in container.iter() if n.tag.endswith('rootfile')),None)
            if not package:raise ValueError('EPUB has no package metadata')
            opf=xml(read(package));ns={'dc':'http://purl.org/dc/elements/1.1/'}
            for field,tag in (('title','title'),('author','creator'),('description','description'),('language','language'),('identifier','identifier')):
                values=[clean(''.join(n.itertext())) for n in opf.findall('.//dc:'+tag,ns)]
                if values:result[field]='; '.join(values)
    elif path.suffix.casefold()=='.pdf':
        with path.open('rb') as stream:
            if b'%PDF-' not in stream.read(1024):raise ValueError('File is not a PDF')
        helper=shutil.which('pdfinfo')
        if helper:
            try:
                info=subprocess.run([helper,str(path)],stdin=subprocess.DEVNULL,start_new_session=True,capture_output=True,text=True,timeout=3,check=True)
                fields=dict(line.split(':',1) for line in info.stdout.splitlines() if ':' in line)
                for field,key in (('title','Title'),('author','Author')):
                    if clean(fields.get(key)):result[field]=clean(fields[key])
            except (OSError,subprocess.SubprocessError):pass
    else:raise ValueError('Choose an EPUB or PDF file')
    return result


def metadata(path):
    try:return _metadata(path)
    except (KeyError,zipfile.BadZipFile,ET.ParseError) as exc:
        raise ValueError('Invalid or unsupported EPUB metadata: '+str(exc)) from exc


def digest(path):
    value=hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda:stream.read(1024*1024),b''):value.update(block)
    return value.hexdigest()


class Shelf:
    def __init__(self,state=None,root=None):
        self.state=Path(state) if state else Path.home()/'.local/share/look/books.json'
        if root is None:
            try:root=json.loads((Path.home()/'.config/look/media_library.json').read_text()).get('root')
            except (OSError,ValueError):root=None
            root=Path(root or '~/Media').expanduser()/'books'
        self.root=Path(root).expanduser().absolute()

    def load(self):
        try:value=json.loads(self.state.read_text())
        except FileNotFoundError:return {'schema':'look-books-v1','entries':[]}
        if not isinstance(value,dict) or not isinstance(value.get('entries'),list):raise ValueError('Invalid bookshelf state')
        return value

    @contextlib.contextmanager
    def edit(self):
        self.state.parent.mkdir(parents=True,exist_ok=True)
        with self.state.with_suffix('.lock').open('a') as lock:
            fcntl.flock(lock,fcntl.LOCK_EX);value=self.load()
            yield value
            fd,temp=tempfile.mkstemp(dir=self.state.parent,prefix='.books-')
            try:
                with os.fdopen(fd,'w') as stream:
                    json.dump(value,stream,ensure_ascii=False);stream.flush();os.fsync(stream.fileno())
                os.replace(temp,self.state)
            finally:
                if os.path.exists(temp):os.unlink(temp)

    def catalog(self):return {'entries':self.load()['entries'],'root':str(self.root)}

    def scan(self):
        if not self.root.is_dir():return dict(self.catalog(),warnings=['Books folder is empty or not mounted'])
        paths=[]
        # Never follow a symlink out of the dedicated library or sweep the home directory.
        for base,dirs,files in os.walk(self.root,followlinks=False):
            dirs[:]=[d for d in dirs if not (Path(base)/d).is_symlink() and not d.startswith('.')]
            paths.extend(Path(base)/name for name in files if not name.startswith('.') and Path(name).suffix.casefold() in FORMATS and not (Path(base)/name).is_symlink())
            if len(paths)>MAX_SCAN_FILES:raise ValueError('Books scan exceeds 10,000 documents; use a smaller library')
        warnings=[]
        with self.edit() as data:
            old={r['path']:r for r in data['entries']};by_id={r['id']:r for r in data['entries']};rows=[]
            for path in sorted(paths):
                try:
                    stat=path.stat();prior=old.get(str(path),{})
                    if prior.get('mtime_ns')==stat.st_mtime_ns and prior.get('bytes')==stat.st_size:rows.append(prior);continue
                    facts=metadata(path);ident=digest(path)
                    prior=prior or by_id.get(ident,{})
                    row=dict(facts,id=ident,path=str(path),bytes=stat.st_size,mtime_ns=stat.st_mtime_ns,added=prior.get('added',time.time()),status='To Read',shelf='',position='')
                    # User edits survive rescans; source bytes and names are never rewritten.
                    for key in ('title','author','status','shelf','position','source_url'):
                        if key in prior:row[key]=prior[key]
                    rows.append(row)
                except (OSError,ValueError,KeyError,zipfile.BadZipFile,ET.ParseError) as exc:
                    warnings.append(clean(path.name+': '+str(exc)))
                    if str(path) in old:rows.append(old[str(path)])
            data['entries']=rows
        return dict(self.catalog(),warnings=warnings)

    def publish(self,temporary,target):
        # Rename works on exFAT as well as native filesystems. Serialize our
        # publishers and refuse collisions without requiring hard-link support.
        self.state.parent.mkdir(parents=True,exist_ok=True)
        with self.state.with_suffix('.publish.lock').open('a') as lock:
            fcntl.flock(lock,fcntl.LOCK_EX)
            if target.is_symlink():raise FileExistsError('Book destination is a symlink')
            if target.exists():
                if digest(target)!=digest(temporary):raise FileExistsError('A different book already has that filename')
                return
            os.rename(temporary,target)

    def import_file(self,source):
        source=Path(source).expanduser().resolve(strict=True);metadata(source)
        self.root.mkdir(parents=True,exist_ok=True);target=self.root/source.name
        if source!=target:
            if target.is_symlink():raise FileExistsError('Book destination is a symlink')
            if target.exists():
                if digest(source)!=digest(target):raise FileExistsError('A different book already has that filename')
            else:
                fd,temp=tempfile.mkstemp(dir=self.root,prefix='.book-');os.close(fd)
                try:
                    shutil.copyfile(source,temp)
                    if digest(source)!=digest(temp):raise OSError('Book copy verification failed')
                    self.publish(Path(temp),target)
                finally:Path(temp).unlink(missing_ok=True)
        self.scan();return next(r for r in self.load()['entries'] if r['path']==str(target))

    def update(self,ident,fields):
        allowed={'title','author','status','shelf','position'}
        if not isinstance(fields,dict) or set(fields)-allowed:raise ValueError('Choose title, author, status, shelf or position')
        if 'status' in fields and fields['status'] not in STATUSES:raise ValueError('Choose To Read, Reading or Finished')
        if any(len(str(v))>2000 for v in fields.values()):raise ValueError('Book field is too long')
        with self.edit() as data:
            row=next((r for r in data['entries'] if r['id']==ident),None)
            if row is None:raise ValueError('Book is no longer in this shelf; refresh')
            for entry in data['entries']:
                if entry['id']==ident:entry.update({k:clean(v) for k,v in fields.items()})
        return row

    def item(self,ident):
        row=next((r for r in self.load()['entries'] if r['id']==ident),None)
        if row is None:raise FileNotFoundError('Book is not cataloged')
        path=Path(row['path'])
        if not path.resolve().is_relative_to(self.root.resolve()) or path.is_symlink() or not path.is_file():raise FileNotFoundError('Book is unavailable on its owner')
        return row,path

    def fetch(self,url):
        parsed=urllib.parse.urlsplit(url)
        if parsed.hostname in {'www.gutenberg.org','gutenberg.org'} and parsed.path.endswith('.opds'):
            with urllib.request.urlopen(url,timeout=15) as response:entry=xml(response.read(MAX_METADATA_BYTES+1))
            links=[n for n in entry.iter() if n.tag.endswith('link') and n.get('type')=='application/epub+zip' and n.get('rel') in {'http://opds-spec.org/acquisition','http://opds-spec.org/acquisition/open-access'}]
            if not links:raise ValueError('This Gutenberg entry has no open EPUB download')
            url=urllib.parse.urljoin(url,links[0].get('href',''));parsed=urllib.parse.urlsplit(url)
        if parsed.scheme!='https' or not parsed.hostname or parsed.username:raise ValueError('Use a public HTTPS EPUB or PDF download URL')
        self.root.mkdir(parents=True,exist_ok=True)
        fd,temp=tempfile.mkstemp(dir=self.root,prefix='.download-');os.close(fd)
        try:
            request=urllib.request.Request(url,headers={'User-Agent':'FutureCrash-LOOK Books (https://github.com/WaltRudyJabsco/FutureCrash-LOOK)'})
            with urllib.request.urlopen(request,timeout=30) as response,open(temp,'wb') as stream:
                if urllib.parse.urlsplit(response.url).scheme!='https':raise ValueError('Book download redirected away from HTTPS')
                total=0
                while block:=response.read(65536):
                    total+=len(block)
                    if total>MAX_DOWNLOAD_BYTES:raise ValueError('Book download exceeds 100 MiB')
                    stream.write(block)
            raw=Path(temp)
            with raw.open('rb') as stream:prefix=stream.read(1024)
            suffix='.pdf' if b'%PDF-' in prefix else '.epub' if zipfile.is_zipfile(raw) else None
            if suffix is None:raise ValueError('Download is not an EPUB or PDF; use a direct document link')
            staged=raw.with_suffix(suffix);raw.rename(staged)
            try:
                facts=metadata(staged)
                if facts['title']==staged.stem:facts['title']=Path(urllib.parse.unquote(parsed.path)).stem or 'Book'
                name=re.sub(r'[^\w .-]','',facts['title'])[:100].strip(' .') or 'Book'
                target=self.root/(name+' - '+digest(staged)[:10]+suffix)
                self.publish(staged,target)
                self.scan()
                row=next(r for r in self.load()['entries'] if r['path']==str(target))
                with self.edit() as data:
                    for entry in data['entries']:
                        if entry['path']==str(target):entry['source_url']=url;row=entry
                return row
            finally:staged.unlink(missing_ok=True)
        finally:Path(temp).unlink(missing_ok=True)


def gutenberg(query):
    url=GUTENBERG+'?'+urllib.parse.urlencode({'query':query})
    with urllib.request.urlopen(url,timeout=15) as response:root=xml(response.read(MAX_METADATA_BYTES+1))
    ns={'a':'http://www.w3.org/2005/Atom'};rows=[]
    for entry in root.findall('a:entry',ns):
        links=[link for link in entry.findall('a:link',ns) if link.get('type')=='application/epub+zip' and link.get('rel') in {'http://opds-spec.org/acquisition','http://opds-spec.org/acquisition/open-access'}]
        if not links:
            links=[n for n in entry.findall('a:link',ns) if n.get('rel')=='subsection' and n.get('href','').endswith('.opds')]
        if not links:continue
        rows.append({'title':clean(entry.findtext('a:title',default='',namespaces=ns)),
                     'author':clean(entry.findtext('a:author/a:name',default='',namespaces=ns) or entry.findtext('a:content',default='',namespaces=ns)),
                     'url':urllib.parse.urljoin(url,links[0].get('href',''))})
    return rows[:20]
