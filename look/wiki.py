"""Offline Kiwix references: explicit owner, fixed setup, verified ZIM downloads."""
from __future__ import annotations
import argparse
import fcntl
import hashlib
import json
import os
from pathlib import Path
import posixpath
import re
import shutil
import subprocess
import sys
import time
import urllib.parse
import urllib.request
import uuid
import book_core
import book_reader
import book_speech
import fabric_files
import media_storage
import look_renderer
from notebook_markdown import safe_text, cell_width

CATALOG='https://library.kiwix.org/catalog/v2/entries'
MAX_ARTICLE_BYTES=4*1024*1024
RESERVE_BYTES=256*1024*1024
TERMINAL={'complete','failed','cancelled'}
HINT_ALPHABET='asdfghjklqwertyuiopzxcvbnm'
MAX_LINKS=200


def hint_code(index):
    return HINT_ALPHABET[index//len(HINT_ALPHABET)]+HINT_ALPHABET[index%len(HINT_ALPHABET)]


def state_root():return Path.home()/'.local/share/look/wiki'
def root():
    try:value=json.loads((Path.home()/'.config/look/wiki.json').read_text()).get('root')
    except (OSError,ValueError):value=None
    return Path(value).expanduser() if value else book_core.Shelf().root.parent/'reference'


def job_path(ident):
    if not re.fullmatch('[a-f0-9]{32}',str(ident)):raise ValueError('Invalid reference job')
    return state_root()/'jobs'/(ident+'.json')


def job(ident):
    value=json.loads(job_path(ident).read_text())
    if value.get('state') not in TERMINAL and value.get('pid'):
        try:os.kill(int(value['pid']),0)
        except OSError:value=dict(value,state='failed',error='Worker stopped; retry explicitly. Partial download retained.')
    return value


def jobs():
    return sorted([job(p.stem) for p in (state_root()/'jobs').glob('*.json')],key=lambda r:r['created'],reverse=True)


def update(ident,**fields):
    path=job_path(ident)
    with path.with_suffix('.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX)
        value=json.loads(path.read_text())
        if value.get('state')=='cancelled':return value
        value.update(fields,updated=time.time())
        book_reader.write_json(path,value);return value


class HTTPSRedirects(urllib.request.HTTPRedirectHandler):
    def redirect_request(self,req,fp,code,msg,headers,newurl):
        if urllib.parse.urlsplit(newurl).scheme!='https':raise ValueError('Reference downloads require HTTPS')
        return super().redirect_request(req,fp,code,msg,headers,newurl)


def online(url,headers=None):
    if urllib.parse.urlsplit(url).scheme!='https':raise ValueError('Reference downloads require HTTPS')
    return urllib.request.build_opener(HTTPSRedirects()).open(urllib.request.Request(url,headers=headers or {}),timeout=30)


def catalog(query='wikipedia'):
    params=urllib.parse.urlencode({'lang':'eng','q':query,'count':100})
    with online(CATALOG+'?'+params) as response:feed=book_core.xml(response.read(book_core.MAX_METADATA_BYTES+1))
    return catalog_rows(feed)


def catalog_rows(feed):
    ns={'a':'http://www.w3.org/2005/Atom'};rows=[]
    entries=[feed] if feed.tag.endswith('}entry') else feed.findall('a:entry',ns)
    for entry in entries:
        def field(name):return entry.findtext('a:'+name,'',ns)
        link=next((n for n in entry.findall('a:link',ns) if n.get('type')=='application/x-zim'),None)
        if link is None:continue
        url=link.get('href','');parts=urllib.parse.urlsplit(url)
        if parts.scheme!='https' or parts.hostname not in {'download.kiwix.org','lb.download.kiwix.org'}:continue
        rows.append({'id':field('id').removeprefix('urn:uuid:'),'title':field('title'),'summary':field('summary'),
                     'name':field('name'),'flavour':field('flavour'),'bytes':int(link.get('length','0')),'url':url})
    return rows



def catalog_entry(ident):
    if not re.fullmatch('[0-9a-f-]{36}',str(ident)):raise ValueError('Choose a catalog entry ID')
    with online('https://library.kiwix.org/catalog/v2/entry/'+ident) as response:data=response.read(book_core.MAX_METADATA_BYTES+1)
    # Kiwix's single-entry response omits the namespace declarations from its feed.
    data=data.replace(b'<entry>',b'<entry xmlns="http://www.w3.org/2005/Atom" xmlns:dc="http://purl.org/dc/terms/">',1)
    rows=catalog_rows(book_core.xml(data))
    if len(rows)!=1 or rows[0]['id']!=ident:raise ValueError('Catalog entry changed; refresh the catalog')
    return rows[0]


def metalink(url):
    parts=urllib.parse.urlsplit(url)
    if parts.scheme!='https' or parts.hostname not in {'download.kiwix.org','lb.download.kiwix.org'} or not parts.path.endswith('.zim.meta4'):raise ValueError('Choose a Kiwix catalog entry')
    with online(url) as response:tree=book_core.xml(response.read(book_core.MAX_METADATA_BYTES+1))
    ns={'m':'urn:ietf:params:xml:ns:metalink'};file=tree.find('m:file',ns)
    if file is None:raise ValueError('Missing Kiwix download metadata')
    name=file.get('name','')
    if Path(name).name!=name or not name.endswith('.zim'):raise ValueError('Invalid archive filename')
    hashes={n.get('type'):n.text for n in file.findall('m:hash',ns)}
    sha=hashes.get('sha-256') or hashes.get('sha256')
    if not sha or not re.fullmatch('[0-9a-fA-F]{64}',sha):raise ValueError('Kiwix did not supply a SHA-256 checksum')
    urls=[n.text for n in file.findall('m:url',ns) if urllib.parse.urlsplit(n.text or '').scheme=='https']
    if not urls:raise ValueError('No secure Kiwix mirror available')
    return {'name':name,'bytes':int(file.findtext('m:size','0',ns)),'sha256':sha.lower(),'url':url.removesuffix('.meta4'),'mirrors':urls}


def archives():
    return [{'id':p.name,'title':p.stem.replace('_',' '),'bytes':p.stat().st_size} for p in sorted(root().glob('*.zim')) if p.is_file() and not p.is_symlink()]


def archive_path(name):
    if Path(str(name)).name!=name or not str(name).endswith('.zim'):raise ValueError('Choose a local ZIM archive')
    path=root()/name
    if path.is_symlink() or not path.is_file():raise ValueError('Archive unavailable on this owner')
    return path


def start(kind,*,entry=None,confirmed=False):
    if confirmed is not True:raise PermissionError('Confirm reference setup or download after reviewing its size and destination')
    state_root().mkdir(parents=True,exist_ok=True)
    with (state_root()/'launch.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX)
        if any(v['state'] not in TERMINAL for v in jobs()):raise ValueError('A reference job is already running; inspect lk wiki jobs')
        ident=uuid.uuid4().hex;value={'id':ident,'kind':kind,'state':'queued','created':time.time(),'root':str(root())}
        if kind=='download':
            if not (state_root()/'libzim-ready').is_file():raise ValueError('Install the offline reader first: lk wiki setup --confirm')
            chosen=catalog_entry(entry)
            value['entry']=chosen
            if chosen['bytes']<=0:raise ValueError('Unknown archive size; choose a catalog entry with a size')
            ancestor=root()
            while not ancestor.exists():ancestor=ancestor.parent
            if shutil.disk_usage(ancestor).free<chosen['bytes']+RESERVE_BYTES:raise ValueError('Insufficient free space at the chosen reference destination')
        elif kind!='setup':raise ValueError('Choose setup or download')
        book_reader.write_json(job_path(ident),value)
        with (state_root()/'jobs'/f'{ident}.log').open('ab') as log:
            proc=subprocess.Popen([sys.executable,str(Path(__file__).resolve()),'--job-worker',ident],stdin=subprocess.DEVNULL,stdout=log,stderr=log,start_new_session=True)
        value=update(ident,pid=proc.pid);return value


def download(ident):
    row=job(ident);info=metalink(row['entry']['url']);folder=Path(row['root']);folder.mkdir(parents=True,exist_ok=True)
    destination=folder/info['name'];partial=folder/('.look-wiki-'+info['sha256'][:16]+'.part')
    if destination.is_symlink() or partial.is_symlink():raise ValueError('Reference staging paths must not be symbolic links')
    if destination.exists():
        if book_core.digest(destination)==info['sha256']:return update(ident,state='complete',file=str(destination))
        raise ValueError('A different file already uses this archive name; choose another destination')
    total=info['bytes']
    if not 0<=row['entry']['bytes']-total<1024 or total<=0:raise ValueError('Archive size changed; refresh the catalog before downloading')
    offset=partial.stat().st_size if partial.exists() else 0
    if offset>total:raise ValueError('Partial download exceeds archive size; remove that partial file before retrying')
    if shutil.disk_usage(folder).free<total-offset+RESERVE_BYTES:raise ValueError('Insufficient free space for this archive')
    if offset<total:
        response=None
        for mirror in [info['url'],*info.get('mirrors',[])[:3]]:
            try:response=online(mirror,{'Range':'bytes='+str(offset)+'-'} if offset else {});break
            except OSError:continue
        if response is None:raise ValueError('Kiwix mirrors unavailable; retry later to resume')
        with response:
            if response.status==206:
                if not response.headers.get('Content-Range','').startswith('bytes '+str(offset)+'-'):raise ValueError('Mirror returned an unexpected byte range')
            elif response.status==200:offset=0
            else:raise ValueError('Mirror did not return archive data')
            with partial.open('ab' if offset else 'wb') as out:
                last=0
                while block:=response.read(1024*1024):
                    if job(ident)['state']=='cancelled':return
                    offset+=len(block)
                    if offset>total:raise ValueError('Mirror exceeded the advertised archive size')
                    out.write(block)
                    if time.monotonic()-last>.5:update(ident,state='downloading',bytes=offset,total=total);last=time.monotonic()
    if partial.stat().st_size!=total:raise ValueError('Incomplete download; retry to resume the retained partial file')
    update(ident,state='verifying',bytes=total,total=total)
    if book_core.digest(partial)!=info['sha256']:raise ValueError('SHA-256 verification failed; remove the partial file before retrying')
    # Verify the ZIM parser can open it before publishing the final filename.
    zim_call('verify',partial)
    if job(ident)['state']=='cancelled':return
    if destination.exists():raise ValueError('Destination appeared during download; retained the verified partial file')
    os.rename(partial,destination)
    update(ident,state='complete',file=str(destination),sha256=info['sha256'])


def run_job(ident):
    with (state_root()/'launch.lock').open('a') as lock:fcntl.flock(lock,fcntl.LOCK_EX)
    try:
        value=job(ident)
        if value['kind']=='setup':
            update(ident,state='installing');venv=state_root()/'venv'
            subprocess.run([sys.executable,'-m','venv',str(venv)],stdin=subprocess.DEVNULL,check=True,timeout=60)
            subprocess.run([str(venv/'bin/python'),'-m','pip','install','libzim'],stdin=subprocess.DEVNULL,check=True,timeout=600)
            zim_call('version',None);(state_root()/'libzim-ready').write_text('libzim\n');update(ident,state='complete')
        else:download(ident)
    except Exception as exc:
        if job(ident)['state']!='cancelled':update(ident,state='failed',error=str(exc))


def zim_call(action,path,query=''):
    python=state_root()/'venv/bin/python'
    if not python.is_file():raise ValueError('Offline reference reader not installed; run lk wiki setup on the owner')
    args=[str(python),str(Path(__file__).resolve()),'--zim-worker',action,str(path or ''),query]
    result=subprocess.run(args,stdin=subprocess.DEVNULL,capture_output=True,text=True,timeout=30)
    if result.returncode:raise ValueError(result.stderr.strip()[-600:] or 'Unable to read this archive')
    if len(result.stdout)>MAX_ARTICLE_BYTES*2:raise ValueError('Reference result too large')
    return json.loads(result.stdout)


class ArticleParser(book_speech.PassageParser):
    def __init__(self,path,wiki_host=None,hints=None,decorate=False,live=False):
        super().__init__();self.links=[];self.path=path;self.wiki_host=wiki_host;self.link=None;self.label=[];self.hints=hints or {};self.decorate=decorate;self.live=live;self.link_start=0;self.images=[]
    def handle_starttag(self,tag,attrs):
        super().handle_starttag(tag,attrs)
        if tag=='a':self.link=dict(attrs).get('href');self.label=[];self.link_start=len(self.current)
        if tag=='img' and not self.skip and len(self.images)<12:
            values=dict(attrs);src=values.get('src','')
            if values.get('width','').isdigit() and int(values['width'])<60:return
            if values.get('height','').isdigit() and int(values['height'])<40:return
            if urllib.parse.urlsplit(src).path.casefold().endswith('.svg'):return
            if self.live:
                candidates=[src]+[part.strip().split()[0] for part in values.get('srcset','').split(',') if part.strip()]
                src=urllib.parse.urljoin('https://en.wikipedia.org/',candidates[-1])
                url=urllib.parse.urlsplit(src)
                if url.scheme!='https' or url.hostname not in {'upload.wikimedia.org','thumb.wikimedia.org'}:return
                src=urllib.parse.urlunsplit(url._replace(query='',fragment=''))
                resource=values.get('resource') or self.link or ''
                file_title=urllib.parse.unquote(resource.removeprefix('./'))
                source=('https://commons.wikimedia.org/wiki/' if '/commons/' in url.path else 'https://en.wikipedia.org/wiki/')+urllib.parse.quote(file_title,safe=':') if file_title.startswith('File:') else src
                image={'url':src,'title':values.get('alt') or file_title or 'Article image','source':source}
            else:
                path=archive_reference(self.path,src)
                if not path:return
                image={'path':path,'title':values.get('alt') or Path(path).name}
            self.images.append(image)
    def handle_data(self,data):
        super().handle_data(data)
        if self.link:self.label.append(data)
    def handle_endtag(self,tag):
        if tag=='a' and self.link:
            url=urllib.parse.urlsplit(self.link)
            target=None
            # Some Kiwix landing pages retain absolute links to their source wiki.
            # Resolve only that archive's known source; never fetch external URLs.
            if self.wiki_host and url.hostname==self.wiki_host and url.scheme in {'http','https',''}:
                if url.path.startswith('/wiki/'):target=urllib.parse.unquote(url.path[6:])
                elif url.path=='/w/index.php':target=(urllib.parse.parse_qs(url.query).get('title') or [None])[0]
            elif self.wiki_host and not url.scheme and not url.netloc and url.path.startswith('/wiki/'):
                target=urllib.parse.unquote(url.path[6:])
            elif not url.scheme and not url.netloc and url.path:
                target=posixpath.join(posixpath.dirname(self.path),urllib.parse.unquote(url.path))
            if target:
                path=posixpath.normpath(target)
                if not path.startswith('../') and not path.startswith('/'):
                    self.links.append({'title':' '.join(''.join(self.label).split()) or path,'path':path})
                    if path in self.hints and not self.skip:
                        if self.decorate:
                            self.current.insert(min(self.link_start,len(self.current)),'\ue000'+self.hints[path]+'\ue001')
                            self.current.append('\ue002')
                        else:self.current.append(' ['+self.hints[path]+']')
            self.link=None
        super().handle_endtag(tag)


def archive_reference(base,href):
    url=urllib.parse.urlsplit(href)
    if url.scheme or url.netloc or not url.path:return None
    path=posixpath.normpath(posixpath.join(posixpath.dirname(base),urllib.parse.unquote(url.path)))
    return path if not path.startswith(('../','/')) else None


def marked_runs(text):
    parts=re.split(r'\ue000([a-z]{2})\ue001(.*?)\ue002',text)
    runs=[{'text':parts[0]}] if parts[0] else []
    for i in range(1,len(parts),3):
        runs.append({'text':parts[i+1],'code':parts[i]})
        if parts[i+2]:runs.append({'text':parts[i+2]})
    return runs


def topic_runs(paragraphs,links):
    codes={row['path'].replace('_',' '):hint_code(i) for i,row in enumerate(links)}
    if not codes:return [[{'text':text}] for text in paragraphs]
    pattern=re.compile(r'(?<!\w)(?:'+'|'.join(re.escape(k) for k in sorted(codes,key=len,reverse=True))+r')(?!\w)')
    return [marked_runs(pattern.sub(lambda m:'\ue000'+codes[m[0]]+'\ue001'+m[0]+'\ue002',text)) if '•' in text else [{'text':text}] for text in paragraphs]


def article_payload(html,path,title,wiki_host=None,live=False,fallback=None):
    # Private markers are internal to the parser, never accepted from source HTML.
    html=html.replace('\ue000','').replace('\ue001','').replace('\ue002','')
    parser=ArticleParser(path,wiki_host=wiki_host,live=live);parser.feed(html);parser.flush()
    if not parser.links and fallback:parser.links=fallback(parser.parts)
    links=list({r['path']:r for r in parser.links}.values())[:MAX_LINKS]
    marked=ArticleParser(path,wiki_host=wiki_host,hints={r['path']:hint_code(i) for i,r in enumerate(links)},decorate=True,live=live)
    marked.feed(html);marked.flush()
    runs=[marked_runs(text) for text in marked.parts] if marked.links else topic_runs(parser.parts,links)
    hinted=[''.join(r['text']+(' ['+r['code']+']' if r.get('code') else '') for r in row) for row in runs]
    return {'title':title,'path':path,'paragraphs':parser.parts,'rich_paragraphs':runs,'hinted_paragraphs':hinted,'links':links,'images':parser.images}


def article_lines(ui,article,width,hints=False):
    """Wrap visible cells before applying palette colors; escape source controls."""
    rich=article.get('rich_paragraphs')
    if rich is None:
        import textwrap
        values=article.get('hinted_paragraphs',article['paragraphs']) if hints else article['paragraphs']
        return [line for text in values for line in [*textwrap.wrap(safe_text(text),width),'']]
    lines=[]
    def paint(row):
        out=[];group='';prior=None
        for char,style in row:
            if style!=prior and group:
                out.append(ui._c(group,prior) if prior else group);group=''
            group+=char;prior=style
        if group:out.append(ui._c(group,prior) if prior else group)
        return ''.join(out)
    for runs in rich:
        chars=[]
        for run in runs:
            style='1;34' if run.get('code') else None
            chars.extend((c,style) for c in safe_text(run['text']))
            if hints and run.get('code'):chars.extend((c,'1;33') for c in ' ['+run['code']+']')
        plain=''.join(c for c,_ in chars);row=[];used=0
        for token in re.finditer(r'\S+\s*',plain):
            word=chars[token.start():token.end()]
            size=sum(cell_width(c) for c,_ in word if not c.isspace())
            if row and used+size>width:
                while row and row[-1][0].isspace():row.pop()
                lines.append(paint(row));row=[];used=0
            for char,style in word:
                cells=cell_width(char)
                if used+cells>width:
                    lines.append(paint(row));row=[];used=0
                if not row and char.isspace():continue
                row.append((char,style));used+=cells
        while row and row[-1][0].isspace():row.pop()
        if row:lines.append(paint(row))
        lines.append('')
    return lines


def topic_hints(paragraphs,links):
    codes={row['path'].replace('_',' '):hint_code(i) for i,row in enumerate(links)}
    if not codes:return list(paragraphs)
    pattern=re.compile(r'(?<!\w)(?:'+'|'.join(re.escape(k) for k in sorted(codes,key=len,reverse=True))+r')(?!\w)')
    return [pattern.sub(lambda m:m[0]+' ['+codes[m[0]]+']',text) if '•' in text else text for text in paragraphs]


def choose_links(ui,fd,rows,title='Links'):
    """One bounded screen: navigation, number+Enter or immediate two-letter hints."""
    if not rows:return None
    index=0;typed=''
    while True:
        width,height=ui.shutil.get_terminal_size((100,30));width=max(20,width)
        controls=ui._media_hints('↑↓ move · Shift-arrows page/ends · Enter open · number then Enter · two letters open · Esc back',width).splitlines()
        page=max(1,height-len(controls)-4)
        index=max(0,min(index,len(rows)-1));top=(index//page)*page
        frame=[ui._c(title,'1;36')+f' · {top+1}–{min(top+page,len(rows))} / {len(rows)}', '']
        colors=ui.terminal_style.list_colors()
        for pos,row in enumerate(rows[top:top+page],top):
            label=('› ' if pos==index else '  ')+f'{pos+1:>3}  [{hint_code(pos)}] '+safe_text(row['title'])
            frame.append(ui.terminal_style.list_row(label,width,pos,pos==index,colors))
        frame+=['']*max(0,page+2-len(frame))
        frame += controls+[ui._c('Choose: '+typed,'1;33')]
        sys.stdout.write(ui._terminal_frame_payload('\n'.join(ui._ansi_clip(line,width) for line in frame)));sys.stdout.flush()
        key=ui._read_tty_key(fd,.25)
        if not key:continue
        if key in {'esc','\x03'}:return None
        if key in {'enter','\r','\n'}:
            if typed.isdigit() and not 1<=int(typed)<=len(rows):continue
            return rows[index]
        if key in {'up','down','shiftup','shiftdown','pageup','pagedown','shiftleft','shiftright','home','end'}:
            typed=''
            if key=='up':index-=1
            elif key=='down':index+=1
            elif key in {'shiftup','pageup'}:index-=page
            elif key in {'shiftdown','pagedown'}:index+=page
            elif key in {'shiftleft','home'}:index=0
            else:index=len(rows)-1
            continue
        if key in {'\b','\x7f'}:typed=typed[:-1];continue
        if len(key)==1 and key.isdigit():
            typed=(typed+key) if typed.isdigit() else key
            if len(typed)>len(str(len(rows))):typed=key
            if 1<=int(typed)<=len(rows):index=int(typed)-1
        elif len(key)==1 and key in HINT_ALPHABET:
            typed=(typed+key) if typed and not typed.isdigit() else key
            if len(typed)==2:
                match=next((r for i,r in enumerate(rows) if hint_code(i)==typed),None)
                if match:return match
                typed=''


def landing_links(archive,paragraphs):
    links=[];seen=set()
    for text in paragraphs:
        if '•' not in text:continue
        for title in text.split('•'):
            path=title.strip().replace(' ','_')
            if not path or path in seen:continue
            seen.add(path)
            try:entry=archive.get_entry_by_path(path)
            except KeyError:continue
            links.append({'title':entry.title,'path':entry.path})
            if len(links)>=MAX_LINKS:return links
    return links


def zim_worker(action,path,query):
    import libzim
    from libzim.reader import Archive
    if action=='version':return {'ok':True}
    archive=Archive(path)
    if action=='verify':return {'ok':True,'articles':archive.article_count}
    if action=='image':
        import base64
        item=archive.get_entry_by_path(query).get_item()
        if item.mimetype not in {'image/jpeg','image/png','image/webp'} or item.size>2*1024*1024:raise ValueError('Archive image unsupported or exceeds 2 MiB')
        return {'mime':item.mimetype,'data':base64.b64encode(bytes(item.content)).decode('ascii')}
    if action=='search':
        from libzim.search import Query,Searcher
        exact=[]
        for candidate in dict.fromkeys(value.replace(' ','_') for value in (query,query[:1].upper()+query[1:])):
            try:
                entry=archive.get_entry_by_path(candidate)
                exact.append({'title':entry.title,'path':entry.path})
                break
            except KeyError:pass
        result=Searcher(archive).search(Query().set_query(query))
        combined=exact+[{'title':r.title,'path':r.path} for r in result.get_results(0,40)]
        return {'entries':list({r['path']:r for r in combined}.values())[:40]}
    entry=archive.get_entry_by_path(query) if query else archive.main_entry
    item=entry.get_item()
    if item.size>MAX_ARTICLE_BYTES:raise ValueError('Article exceeds 4 MiB')
    host='en.wikipedia.org' if Path(path).name.startswith('wikipedia_en_') else None
    html=bytes(item.content).decode('utf-8',errors='replace')
    return article_payload(html,entry.path,entry.title,wiki_host=host,fallback=(lambda parts:landing_links(archive,parts)) if not query else None)


def local(action='status',**payload):
    if action=='status':return {'ok':True,'root':str(root()),'archives':archives(),'jobs':jobs(),'reader_installed':(state_root()/'libzim-ready').is_file()}
    if action=='catalog':return {'entries':catalog(str(payload.get('query') or 'wikipedia'))}
    if action=='setup':return start('setup',confirmed=payload.get('confirm'))
    if action=='fetch':return start('download',entry=payload.get('id'),confirmed=payload.get('confirm'))
    if action=='configure':
        destination=Path(str(payload.get('root') or '')).expanduser()
        if not destination.is_absolute():raise ValueError('Choose an absolute reference directory')
        if any(v['state'] not in TERMINAL for v in jobs()):raise ValueError('Finish or cancel reference jobs before changing destination')
        destination.mkdir(parents=True,exist_ok=True)
        book_reader.write_json(Path.home()/'.config/look/wiki.json',{'root':str(destination.resolve())});return local()
    if action=='cancel':
        value=job(payload.get('id'))
        if value['kind']=='setup':raise ValueError('Let package setup finish before updating; download cancellation is available')
        if value['state'] not in TERMINAL:return update(value['id'],state='cancelled')
        return value
    if action in {'search','article','image'}:return zim_call(action,archive_path(payload.get('archive')),str(payload.get('query') or ''))
    raise ValueError('Unknown reference action')


def request(action='status',node='local',**payload):
    if node=='local':return local(action,**payload)
    return fabric_files.request('/v1/wiki',{'target':node},json.dumps(dict(payload,action=action)).encode(),timeout=8 if action=='status' else 45)


def main(argv=None,ui=None):
    parser=argparse.ArgumentParser(prog='lk wiki',description=__doc__)
    parser.add_argument('action',nargs='?',default='shelf',choices=['shelf','status','setup','catalog','fetch','jobs','cancel','configure','search','article'])
    parser.add_argument('values',nargs='*');parser.add_argument('--node');parser.add_argument('--root');parser.add_argument('--archive');parser.add_argument('--confirm',action='store_true');parser.add_argument('--json',action='store_true')
    source=parser.add_mutually_exclusive_group()
    source.add_argument('--online',action='store_true',help='Use live English Wikipedia on this computer')
    source.add_argument('--offline',action='store_true',help='Force the saved local/Fabric archive; no live requests')
    args=parser.parse_args(argv);owner=args.node or media_storage.settings()['node']
    try:
        if args.action=='shelf':return desk(ui,owner,live=args.online)
        action='status' if args.action=='jobs' else args.action
        fields={'query':' '.join(args.values),'id':' '.join(args.values),'archive':args.archive,'root':args.root,'confirm':args.confirm}
        if args.online:
            import wiki_online
            if action=='article':value=wiki_online.article(fields['query'])
            elif action=='search':value=wiki_online.search(fields['query'])
            elif action=='status':value={'source':'live English Wikipedia','url':wiki_online.HOST,'reader_required':False}
            else:raise ValueError('Live mode supports shelf, search, article and status; --offline selects archive tools')
        else:value=request(action,node=owner,**fields)
        if args.json:print(json.dumps(value,ensure_ascii=False,indent=2))
        elif action=='catalog':
            for row in value['entries']:print(row['id']+' · '+row['title']+' · '+row['flavour']+' · '+format_bytes(row['bytes']))
        else:print(json.dumps(value,ensure_ascii=False,indent=2))
        return 0
    except (OSError,ValueError,RuntimeError,subprocess.SubprocessError) as exc:print('LOOK Wiki: '+safe_text(str(exc)));return 1


def format_bytes(value):return f'{value/(1024**3):.1f} GiB' if value>=1024**3 else f'{value/(1024**2):.1f} MiB'


def desk(ui,owner,live=False):
    import termios,tty
    if not ui or not sys.stdin.isatty():raise ValueError('Use lk wiki status --json outside a terminal')
    fd=sys.stdin.fileno();old=termios.tcgetattr(fd);mode='archives';index=0;notice='d finds downloadable collections · i sets up the offline reader'
    archive=None;rows=[];status={};saved_status=None
    def ask(label):
        termios.tcsetattr(fd,termios.TCSADRAIN,old)
        try:
            print('\n'+ui._c(label,'1;36'))
            value,cancelled=look_renderer.prompt_line('› ')
            return None if cancelled else value.strip()
        finally:tty.setcbreak(fd)
    def shelf_rows(value):
        return [{'id':'live','kind':'live','title':'Live Wikipedia · web (internet required)'},*value.get('archives',[])]
    def refresh():
        nonlocal saved_status
        if live:return saved_status or {'root':'Saved owner not loaded','reader_installed':False,'archives':[],'jobs':[]}
        value=request(node=owner);saved_status=value;return value
    def switch_source():
        nonlocal live,status,rows,mode,index,archive,saved_status
        if live:
            replacement=request(node=owner);saved_status=replacement
        else:replacement=saved_status or {'root':'Saved owner not loaded','reader_installed':False,'archives':[],'jobs':[]}
        live=not live;status=replacement;rows=shelf_rows(status);mode='archives';index=0;archive=None
        return 'Live Wikipedia selected' if live else 'Saved Fabric archive selected · no live Wikipedia requests'
    def fetch_article(action,**payload):
        if live:
            import wiki_online
            return wiki_online.article(payload.get('query','')) if action=='article' else wiki_online.search(payload.get('query',''))
        return request(action,node=owner,archive=archive,**payload)
    def article_view(path):
        history=[];top=0;hinting=False;typed='';layout=None;lines=[];article_notice=''
        while True:
            article=fetch_article('article',query=path);layout=None
            while True:
                width,height=ui.shutil.get_terminal_size((100,30));width=max(20,width)
                controls=ui._media_hints('↑↓ scroll · Shift-arrows page/ends · / search archive · l links ('+str(len(article['links']))+') · f link hints · i images · v live/saved · b back · y copy passage · Esc shelf',width).splitlines()
                if hinting:controls=['LINK HINTS '+typed+' · two letters open · arrows scroll · Esc cancels']
                page=max(1,height-len(controls)-2)
                if layout!=(width,hinting):lines=article_lines(ui,article,width,hinting);layout=(width,hinting)
                top=max(0,min(top,max(0,len(lines)-page)))
                frame=[ui._c(safe_text(article['title']),'1;36')+' · '+(('STALE CACHED WIKIPEDIA' if article.get('stale') else 'CACHED WIKIPEDIA' if article.get('cached') else 'LIVE WIKIPEDIA') if live else 'SAVED ARCHIVE · owner '+safe_text(owner)),*lines[top:top+page]]
                frame+=['']*max(0,page+1-len(frame))
                frame+=controls
                if article_notice:frame[-1]=ui._c(safe_text(article_notice),'33')+' · '+frame[-1]
                if live and not hinting:frame[-1]=ui._c('Wikipedia contributors · CC BY-SA 4.0 · ','2')+frame[-1]
                if hinting:
                    frame[-1]=ui._c(frame[-1],'1;33')
                    codes={hint_code(i) for i in range(len(article['links']))}
                    frame=[re.sub(r'\[([a-z]{2})\]',lambda m:ui._c(m[0],'1;33') if m[1] in codes else m[0],line) for line in frame]
                sys.stdout.write(ui._terminal_frame_payload('\n'.join(ui._ansi_clip(line,width) for line in frame)));sys.stdout.flush()
                key=ui._read_tty_key(fd,.25)
                if hinting:
                    if key=='esc':hinting=False;typed='';continue
                    if len(key)==1 and key in HINT_ALPHABET:
                        typed+=key
                        if len(typed)==2:
                            match=next((r for i,r in enumerate(article['links']) if hint_code(i)==typed),None)
                            typed=''
                            if match:history.append((path,top));path=match['path'];top=0;hinting=False;break
                        continue
                    if key in {'\b','\x7f'}:typed=typed[:-1];continue

                if key in {'esc','q','\x03'}:return
                if key=='up':top-=1
                elif key=='down':top+=1
                elif key in {'shiftup','pageup'}:top-=page
                elif key in {'shiftdown','pagedown',' '}:top+=page
                elif key in {'shiftleft','home'}:top=0
                elif key in {'shiftright','end'}:top=len(lines)
                elif key=='y':look_renderer.copy_text(ui._strip_ansi('\n'.join(lines[top:top+page]))+('\n'+article.get('attribution','')+'\n'+article.get('source_url','') if live else ''))
                elif key=='f':hinting=True;typed=''
                elif key=='v':return 'switch'
                elif key=='i':
                    import wiki_images
                    article_notice=wiki_images.gallery(ui,fd,article,live=live,archive=archive or '',owner=owner)
                elif key=='b' and history:path,top=history.pop();break
                elif key=='/':
                    query=ask('Search this saved archive · Enter cancels')
                    if query:
                        found=fetch_article('search',query=query)['entries']
                        if found:
                            chosen=choose_links(ui,fd,found,'Search: '+query)
                            if chosen:history.append((path,top));path=chosen['path'];top=0;break
                        else:ask('No matching articles · Enter returns')
                elif key=='l':
                    if not article['links']:
                        ask('This page has no internal links · / searches the archive · Enter returns');continue
                    chosen=choose_links(ui,fd,article['links'])
                    if chosen:history.append((path,top));path=chosen['path'];top=0;break
    try:
        tty.setcbreak(fd)
        if os.environ.get('KITTY_WINDOW_ID') or os.environ.get('TERM')=='xterm-kitty':sys.stdout.write('\x1b_Ga=d,d=a,q=2\x1b\\')
        sys.stdout.write('\x1b[0m\x1b[2J\x1b[HOFFLINE REFERENCES · opening…');sys.stdout.flush()
        try:status=refresh()
        except (OSError,ValueError,RuntimeError) as exc:status={'root':'Owner unavailable: '+str(exc),'archives':[],'jobs':[],'reader_installed':False}
        rows=shelf_rows(status)
        notice=('Live Wikipedia · / searches · Enter opens the main page' if live else '/ searches the selected saved archive · Enter opens its landing page') if rows else 'No archives on this owner · o chooses another owner · d finds downloads'
        while True:
            width,height=ui.shutil.get_terminal_size((100,30));width=max(20,width);page=max(1,height-9)
            index=max(0,min(index,max(0,len(rows)-1)));selected=rows[index] if rows else None;top=max(0,index-page+1)
            frame=[ui._c('LOOK WIKI','1;36')+' · '+('LIVE WIKIPEDIA' if live else 'SAVED · '+safe_text(owner))+' · '+mode,
                   ui._c('Source: ' if live else 'Archive folder: ','2')+safe_text('https://en.wikipedia.org' if live else status['root'])+' · '+ui._c('no ZIM reader needed' if live else 'reader ready' if status.get('reader_installed') else 'reader not installed','32' if status.get('reader_installed') else '33')]
            colors=ui.terminal_style.list_colors()
            for i,row in enumerate(rows[top:top+page],top):
                text=('› ' if i==index else '  ')+safe_text(row['title'])
                if row.get('flavour'):text+=' · '+safe_text(row['flavour'])
                if row.get('bytes'):text+=' · '+format_bytes(row['bytes'])
                frame.append(ui.terminal_style.list_row(text,width,i,i==index,colors))
            frame+=['']*max(0,page+2-len(frame))
            if status.get('jobs'):
                latest=status['jobs'][0];total=latest.get('total',0);progress=f' · {100*latest.get("bytes",0)/total:.1f}%' if total else ''
                frame.append(ui._c('Job: ','1;36')+safe_text(latest['state']+progress+' · '+str(latest.get('error') or latest['kind'])))
            frame += [ui._media_hints('↑↓ select · Shift-arrows page/ends · Enter open/download · / search · v live/saved · o owner · d download catalog · i reader setup · r refresh · x cancel download · Esc back',width),safe_text(notice)]
            sys.stdout.write(ui._terminal_frame_payload('\n'.join(ui._ansi_clip(line,width) for line in frame)));sys.stdout.flush()
            key=ui._read_tty_key(fd,.25)
            if not key:continue
            if key in {'esc','q','\x03'}:
                if mode!='archives':mode='archives';rows=shelf_rows(status);index=0;continue
                return 0
            if key=='up':index-=1;continue
            if key=='down':index+=1;continue
            if key in {'shiftup','pageup'}:index-=page;continue
            if key in {'shiftdown','pagedown'}:index+=page;continue
            if key in {'shiftleft','home'}:index=0;continue
            if key in {'shiftright','end'}:index=len(rows)-1;continue
            try:
                if key=='r':status=refresh();rows=shelf_rows(status);mode='archives';notice='Refreshed'
                elif key=='v':notice=switch_source()
                elif live and key in {'o','d','i','x'}:notice='Saved-archive controls · v selects the saved Fabric archive'
                elif key=='o':
                    choices=['local',*[n.node for n in fabric_files.nodes()]]
                    answer=ask('Reference owner · '+', '.join(choices)+' · Enter cancels')
                    if answer:
                        if answer not in choices:raise ValueError('Choose one of the listed Fabric owners')
                        replacement=request(node=answer)
                        owner=answer;status=replacement;rows=shelf_rows(status);mode='archives';archive=None;index=0
                        notice='Selected owner '+owner
                elif key=='d':rows=request('catalog',node=owner,query='wikipedia')['entries'];mode='catalog';index=0
                elif key=='/':
                    text=ask('Search downloadable collections' if mode=='catalog' else 'Search this offline archive')
                    if text:
                        if mode=='catalog':rows=request('catalog',node=owner,query=text)['entries']
                        elif archive or selected:
                            if mode=='archives':archive=selected['id']
                            rows=fetch_article('search',query=text)['entries'];mode='articles'
                        index=0
                elif key=='i':
                    if status.get('reader_installed'):notice='Reader already installed on '+owner+' · / searches the selected archive';continue
                    answer=ask('Install optional libzim in an isolated environment on '+owner+'? y/N')
                    if answer and answer.casefold()=='y':request('setup',node=owner,confirm=True);status=refresh();notice='Reader setup started · r refreshes status'
                elif key=='x':
                    active=next((v for v in status['jobs'] if v['state'] not in TERMINAL),None)
                    if active:request('cancel',node=owner,id=active['id']);status=refresh();notice='Download cancelled; partial file retained for retry'
                elif key in {'enter','\r','\n'} and selected:
                    if mode=='catalog':
                        answer=ask('Download '+selected['title']+' · '+selected['flavour']+' · '+format_bytes(selected['bytes'])+' to '+owner+':'+status['root']+'? y/N')
                        if answer and answer.casefold()=='y':request('fetch',node=owner,id=selected['id'],confirm=True);status=refresh();notice='Download started · r refreshes progress'
                    elif mode=='archives':
                        if selected.get('kind')=='live':live=True
                        elif live:
                            status=request(node=owner);saved_status=status;live=False
                        archive=selected['id']
                        if article_view('')=='switch':notice=switch_source()
                    elif article_view(selected['path'])=='switch':notice=switch_source()
            except (OSError,ValueError,RuntimeError,subprocess.SubprocessError) as exc:notice=safe_text(str(exc))
    finally:termios.tcsetattr(fd,termios.TCSADRAIN,old)


if __name__=='__main__':
    if len(sys.argv)==3 and sys.argv[1]=='--job-worker':run_job(sys.argv[2])
    elif len(sys.argv)==5 and sys.argv[1]=='--zim-worker':
        try:print(json.dumps(zim_worker(*sys.argv[2:]),ensure_ascii=False))
        except Exception as exc:print(str(exc),file=sys.stderr);raise SystemExit(1)
    else:raise SystemExit(main())
