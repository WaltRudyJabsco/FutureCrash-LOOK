"""Public-domain museum adapters and a bounded, offline-first local collection."""
from __future__ import annotations
import hashlib
import json
import math
import uuid
import os
from pathlib import Path
import re
import threading
import time
import urllib.parse
import urllib.request

MAX_IMAGE_BYTES=20*1024*1024
MAX_JSON_BYTES=8*1024*1024
MAX_COLLECTION_BYTES=3*1024*1024*1024
MAX_PACK_ITEMS=1000
REQUEST_INTERVAL=.3
SEARCH_BUDGET_SECONDS=45
SOURCES=('met','aic')
# These editorial themes define the starter exhibition; results are not random.
THEMES=('landscape','portrait','Japanese woodblock','flowers','ancient Egypt',
        'Chinese painting','Indian sculpture','Islamic ceramics','Dutch painting','Impressionism',
        'architecture','birds','ocean','textile','musical instrument','African sculpture',
        'Greek vase','medieval manuscript','photography','still life')
HOSTS={'collectionapi.metmuseum.org','images.metmuseum.org','api.artic.edu','www.artic.edu'}
_NETWORK_LOCK=threading.Lock()
_LAST_REQUEST=0.0


def root():return Path.home()/'.local/share/future-crash-look/museum'
def catalog_path():return root().parent/'museum.json'
def identity(value):
    if not re.fullmatch(r'(met|aic)-[1-9][0-9]{0,9}',str(value)):raise ValueError('Choose a museum artwork ID, such as aic-27992')
    source,number=value.split('-');return source,int(number)
def clean(value):return re.sub(r'[\x00-\x1f\x7f-\x9f]',' ',re.sub('<[^>]*>','',str(value or ''))).strip()[:4000]
def allowed(url):
    parsed=urllib.parse.urlsplit(url)
    if parsed.scheme!='https' or parsed.hostname not in HOSTS or parsed.username or parsed.password or parsed.port not in (None,443):raise ValueError('Untrusted museum image or API address')
    return url
class Redirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self,req,fp,code,msg,headers,newurl):
        allowed(newurl);return super().redirect_request(req,fp,code,msg,headers,newurl)
def fetch(url,limit=MAX_JSON_BYTES):
    global _LAST_REQUEST
    allowed(url)
    with _NETWORK_LOCK:
        time.sleep(max(0,REQUEST_INTERVAL-(time.monotonic()-_LAST_REQUEST)))
        _LAST_REQUEST=time.monotonic()
    request=urllib.request.Request(url,headers={'User-Agent':'LOOK-Museum/1.0 (public-domain collection browser)'})
    with urllib.request.build_opener(Redirect).open(request,timeout=20) as response:
        data=response.read(limit+1)
    if len(data)>limit:raise ValueError('Museum response exceeds size limit')
    return data

def get_json(url):return json.loads(fetch(url))
def record(source,data):
    if source=='met':
        if not data.get('isPublicDomain') or not data.get('primaryImage'):return None
        result=dict(id='met-'+str(data['objectID']),title=data.get('title'),artist=data.get('artistDisplayName'),date=data.get('objectDate'),medium=data.get('medium'),culture=data.get('culture'),description=data.get('creditLine'),image_url=data.get('primaryImageSmall') or data['primaryImage'],source_url='https://www.metmuseum.org/art/collection/search/'+str(data['objectID']),museum='The Metropolitan Museum of Art')
    else:
        if not data.get('is_public_domain') or not data.get('image_id'):return None
        image=str(data['image_id'])
        if not re.fullmatch('[a-zA-Z0-9-]+',image):raise ValueError('Invalid museum image identity')
        result=dict(id='aic-'+str(data['id']),title=data.get('title'),artist=data.get('artist_display'),date=data.get('date_display'),medium=data.get('medium_display'),culture=data.get('place_of_origin'),description=data.get('description') or data.get('credit_line'),image_url=f'https://www.artic.edu/iiif/2/{image}/full/1686,/0/default.jpg',source_url='https://www.artic.edu/artworks/'+str(data['id']),museum='Art Institute of Chicago')
    result={k:clean(v) for k,v in result.items()};identity(result['id']);allowed(result['image_url'])
    result.update(source=source,rights='CC0',rights_url='https://creativecommons.org/publicdomain/zero/1.0/',downloaded=False)
    return result

def detail(ident):
    source,number=identity(ident)
    url=f'https://collectionapi.metmuseum.org/public/collection/v1/objects/{number}' if source=='met' else f'https://api.artic.edu/api/v1/artworks/{number}'
    data=get_json(url);result=record(source,data if source=='met' else data['data'])
    if not result:raise ValueError('No open-access image is available for this work')
    return result

def discover(source,query,page=1,limit=20):
    if source not in SOURCES:raise ValueError('Choose met or aic')
    query=str(query).strip()[:150]
    if not query:raise ValueError('Enter an artist, subject or period')
    page=int(page);limit=int(limit)
    if not 1<=page<=50 or not 1<=limit<=40:raise ValueError('Invalid museum page size')
    rows=[]
    if source=='met':
        params=urllib.parse.urlencode(dict(q=query,hasImages='true',offset=(page-1)*limit,limit=limit))
        data=get_json('https://collectionapi.metmuseum.org/public/collection/v1.1/search?'+params)
        deadline=time.monotonic()+SEARCH_BUDGET_SECONDS
        for number in (data.get('objectIDs') or [])[:limit]:
            if time.monotonic()>deadline:break
            try:rows.append(detail('met-'+str(number)))
            except (ValueError,OSError):continue
        more=page*limit<int(data.get('total',0))
    else:
        params=dict(q=query,page=page,limit=limit,query={'term':{'is_public_domain':True}},fields=['id','title','artist_display','date_display','medium_display','place_of_origin','description','credit_line','is_public_domain','image_id'])
        data=get_json('https://api.artic.edu/api/v1/artworks/search?'+urllib.parse.urlencode({'params':json.dumps(params,separators=(',',':'))}))
        rows=[row for item in data.get('data',[]) if (row:=record('aic',item))]
        more=page<int(data.get('pagination',{}).get('total_pages',page))
    return {'items':rows,'more':more,'page':page,'source':source,'query':query}


FEATURED_NAMES={'met':'Met Highlights','aic':'Art Institute Featured'}
FEATURED_PAGE_SIZE=40
FEATURED_MAX_PAGES=250

def featured_ids(source,page):
    if source not in SOURCES:raise ValueError('Choose met or aic')
    if source=='met':
        params=dict(q='*',isHighlight='true',hasImages='true',offset=(page-1)*FEATURED_PAGE_SIZE,limit=FEATURED_PAGE_SIZE)
        data=get_json('https://collectionapi.metmuseum.org/public/collection/v1.1/search?'+urllib.parse.urlencode(params))
        return ['met-'+str(x) for x in data.get('objectIDs',[])],page*FEATURED_PAGE_SIZE<int(data.get('total',0))
    params=dict(page=page,limit=FEATURED_PAGE_SIZE,query={'bool':{'filter':[{'term':{'is_boosted':True}},{'term':{'is_public_domain':True}},{'exists':{'field':'image_id'}}]}},fields=['id'])
    data=get_json('https://api.artic.edu/api/v1/artworks/search?'+urllib.parse.urlencode({'params':json.dumps(params,separators=(',',':'))}))
    return ['aic-'+str(x['id']) for x in data.get('data',[])],page<int(data.get('pagination',{}).get('total_pages',page))


def atomic(path,data):
    path.parent.mkdir(parents=True,exist_ok=True)
    temp=path.with_name('.'+path.name+'.'+str(threading.get_ident())+'.tmp')
    try:temp.write_bytes(data);os.replace(temp,path)
    finally:temp.unlink(missing_ok=True)


class Museum:
    def __init__(self,folder=None,catalog=None):
        self.root=Path(folder or root());self.catalog=Path(catalog or (catalog_path() if folder is None else self.root/'catalog.json'))
        self.lock=threading.RLock();self.worker=None;self.stop=threading.Event()
        self.cache={}
        with self.lock:
            state=self.read()
            if state.get('job',{}).get('state')=='running':
                state['job']['state']='interrupted';self.write(state)
    def read(self):
        try:return json.loads(self.catalog.read_text())
        except FileNotFoundError:return {'schema':1,'items':{},'job':{}}
    def write(self,state):atomic(self.catalog,json.dumps(state,ensure_ascii=False).encode())
    def image(self,ident):
        identity(ident);path=self.root/'images'/(ident+'.jpg')
        if not path.is_file() or path.is_symlink():raise ValueError('Artwork is not downloaded on this node')
        return path
    def snapshot(self,query=''):
        with self.lock:
            state=self.read();rows=[]
            for item in state['items'].values():
                row=dict(item)
                try:row['downloaded']=self.image(row['id']).is_file()
                except ValueError:row['downloaded']=False
                if not query or str(query).casefold() in ' '.join(str(row.get(k,'')) for k in ('title','artist','date','medium','culture','collection')).casefold():rows.append(row)
            return {'items':sorted(rows,key=lambda x:x['title'].casefold()),'job':state.get('job',{}),'bytes':sum(x.get('bytes',0) for x in state['items'].values()),'limit_bytes':MAX_COLLECTION_BYTES,'collections':state.get('collections',{})}
    def search(self,source,query,page=1):
        result=discover(source,query,page)
        with self.lock:
            known=self.read()['items']
            for row in result['items']:
                row['downloaded']=bool(known.get(row['id'],{}).get('downloaded')) and (self.root/'images'/(row['id']+'.jpg')).is_file()
                self.cache[row['id']]=row
            if len(self.cache)>2000:self.cache={x['id']:x for x in result['items']}
        return result
    def store(self,row,data,collection='Personal collection'):
        identity(row['id'])
        if row.get('rights')!='CC0':raise ValueError('Only verified open-access artwork can be saved')
        if len(data)>MAX_IMAGE_BYTES or not (data.startswith(b'\xff\xd8\xff') or data.startswith(b'\x89PNG\r\n\x1a\n')):raise ValueError('Invalid or oversized museum image')
        with self.lock:
            state=self.read();old=state['items'].get(row['id'],{})
            total=sum(x.get('bytes',0) for x in state['items'].values())-old.get('bytes',0)+len(data)
            if total>MAX_COLLECTION_BYTES:raise ValueError('Museum collection reached its 3 GiB storage budget')
            atomic(self.root/'images'/(row['id']+'.jpg'),data)
            result=dict(row,downloaded=True,bytes=len(data),sha256=hashlib.sha256(data).hexdigest(),collection=old.get('collection') or collection,added=old.get('added',time.time()),favorite=old.get('favorite',row.get('favorite',False)),collections=old.get('collections',row.get('collections',[])))
            state['items'][row['id']]=result;self.write(state);return result
    def save(self,ident,collection='Personal collection'):
        identity(ident)
        with self.lock:
            old=self.read()['items'].get(ident)
            if old and (self.root/'images'/(ident+'.jpg')).is_file():return old
            row=self.cache.get(ident)
        row=row or detail(ident)
        return self.store(row,fetch(row['image_url'],MAX_IMAGE_BYTES),collection)
    def favorite(self,ident):
        with self.lock:
            state=self.read()
            if ident not in state['items']:raise ValueError('Download this work before favoriting it')
            row=state['items'][ident];row['favorite']=not row.get('favorite',False);self.write(state)
        return self.snapshot()
    def start_pack(self,count=1000):
        count=int(count)
        if not 1<=count<=MAX_PACK_ITEMS:raise ValueError('Starter pack size must be 1–1000')
        with self.lock:
            if self.worker and self.worker.is_alive():raise ValueError('A starter pack is already running')
            self.stop.clear();state=self.read();state['job']={'state':'running','requested':count,'saved':0,'errors':[],'theme':'Starting'};self.write(state)
            self.worker=threading.Thread(target=self._pack,args=(count,),daemon=True);self.worker.start()
        return self.snapshot()
    def start_featured(self,count=500,source='both'):
        count=int(count)
        if not 1<=count<=500:raise ValueError('Featured size must be 1–500 per museum')
        if source not in (*SOURCES,'both'):raise ValueError('Choose met, aic or both')
        sources=SOURCES if source=='both' else (source,)
        with self.lock:
            if self.worker and self.worker.is_alive():raise ValueError('A collection download is already running')
            state=self.read();collections=state.setdefault('collections',{});groups={}
            for name in sources:
                ident=uuid.uuid5(uuid.NAMESPACE_URL,'look-museum-featured:'+name).hex
                if ident not in collections and len(collections)>=200:raise ValueError('The library supports up to 200 named collections')
                collections.setdefault(ident,{'name':FEATURED_NAMES[name],'selection':'Museum highlights' if name=='met' else 'Museum-boosted search results'})
                groups[name]=ident
            self.stop.clear();state['job']={'state':'running','kind':'featured','requested':count*len(sources),'saved':0,'counts':{},'errors':[],'theme':'Museum selections'};self.write(state)
            self.worker=threading.Thread(target=self._featured,args=(count,groups),daemon=True);self.worker.start()
        return self.snapshot()

    def _featured(self,count,groups):
        errors=[];counts={name:0 for name in groups}
        try:
            for source,collection in groups.items():
                seen=set()
                for page in range(1,FEATURED_MAX_PAGES+1):
                    if self.stop.is_set() or counts[source]>=count:break
                    try:ids,more=featured_ids(source,page)
                    except (OSError,ValueError) as exc:errors.append(source+': '+str(exc));break
                    for ident in ids:
                        if self.stop.is_set() or counts[source]>=count:break
                        if ident in seen:continue
                        seen.add(ident)
                        try:
                            self.save(ident,FEATURED_NAMES[source])
                            with self.lock:
                                state=self.read();row=state['items'][ident]
                                row['collections']=sorted(set(row.get('collections',[]))|{collection});self.write(state)
                            counts[source]+=1
                        except (OSError,ValueError) as exc:
                            if 'storage budget' in str(exc):raise
                            errors.append(ident+': '+str(exc))
                        self._job(saved=sum(counts.values()),counts=dict(counts),errors=errors[-20:],theme=FEATURED_NAMES[source])
                    if not more:break
            total=sum(counts.values())
            self._job(state='cancelled' if self.stop.is_set() else 'complete' if total==count*len(groups) else 'partial',saved=total,counts=counts,errors=errors[-20:])
        except Exception as exc:self._job(state='failed',errors=(errors+[str(exc)])[-20:])

    def start_sync(self,rows,loader,collections=None):
        rows=[row for row in rows if row.get('downloaded')][:MAX_PACK_ITEMS]
        with self.lock:
            if self.worker and self.worker.is_alive():raise ValueError('A collection download is already running')
            self.stop.clear();state=self.read()
            if collections:
                for ident,value in list(collections.items())[:200]:
                    if re.fullmatch('[a-f0-9]{32}',ident):state.setdefault('collections',{}).setdefault(ident,{'name':clean(value.get('name',''))[:80]})
            state['job']={'state':'running','requested':len(rows),'saved':0,'errors':[],'theme':'Copying from Fabric'};self.write(state)
            def run():
                saved=0;errors=[]
                for row in rows:
                    if self.stop.is_set():break
                    try:
                        try:existing=self.image(row['id'])
                        except ValueError:existing=None
                        if not existing or hashlib.sha256(existing.read_bytes()).hexdigest()!=row.get('sha256'):
                            data=loader(row)
                            if hashlib.sha256(data).hexdigest()!=row.get('sha256'):raise ValueError('Artwork transfer checksum mismatch')
                            self.store(row,data,row.get('collection','Pinned collection'))
                        saved+=1;self._job(saved=saved)
                    except Exception as exc:errors.append(str(exc));self._job(errors=errors[-20:])
                self._job(state='cancelled' if self.stop.is_set() else 'partial' if errors else 'complete',saved=saved)
            self.worker=threading.Thread(target=run,daemon=True);self.worker.start()
        return self.snapshot()

    def _pack(self,count):
        seen=set();errors=[];theme_counts={};per_theme=math.ceil(count/(len(THEMES)*len(SOURCES)))
        try:
            # Round-robin themes/sources avoid filling the pack from one department.
            for page in range(1,6):
                for theme in THEMES:
                    for source in SOURCES:
                        if self.stop.is_set() or len(seen)>=count:break
                        key=(source,theme)
                        if theme_counts.get(key,0)>=per_theme:continue
                        try:
                            result=self.search(source,theme,page)
                            for row in result['items']:
                                if self.stop.is_set() or len(seen)>=count or theme_counts.get(key,0)>=per_theme:break
                                if row['id'] in seen:continue
                                self.save(row['id'],'Starter · '+theme);seen.add(row['id']);theme_counts[key]=theme_counts.get(key,0)+1
                                self._job(saved=len(seen),theme=theme)
                        except Exception as exc:
                            if 'storage budget' in str(exc):raise
                            errors.append(source+': '+str(exc));self._job(errors=errors[-20:],theme=theme)
                    if self.stop.is_set() or len(seen)>=count:break
                if self.stop.is_set() or len(seen)>=count:break
            self._job(state='cancelled' if self.stop.is_set() else 'complete' if len(seen)>=count else 'partial',saved=len(seen))
        except Exception as exc:self._job(state='failed',errors=[str(exc)])
    def _job(self,**fields):
        with self.lock:
            state=self.read();state['job'].update(fields);self.write(state)
    def collection_change(self,data):
        with self.lock:
            state=self.read();collections=state.setdefault('collections',{})
            action=data['action']
            if action=='collection-create':
                if len(collections)>=200:raise ValueError('The library supports up to 200 named collections')
                name=clean(data.get('name','')).strip()
                if not name or len(name)>80:raise ValueError('Choose a collection name of 1–80 characters')
                if any(row['name'].casefold()==name.casefold() for row in collections.values()):raise ValueError('That collection already exists')
                ident=uuid.uuid4().hex;collections[ident]={'name':name}
            else:
                ident=str(data.get('collection',''))
                if ident not in collections:raise ValueError('Choose an existing collection')
                row=state['items'].get(data.get('id',''))
                if not row:raise ValueError('Save the artwork to the library first')
                membership=set(row.get('collections',[]))
                if action=='collection-add':membership.add(ident)
                elif action=='collection-remove':membership.discard(ident)
                else:raise ValueError('Unknown collection action')
                row['collections']=sorted(membership)
            self.write(state)
        return dict(self.snapshot(),active_collection=ident)

    def change(self,data):
        action=data.get('action')
        if action in {'collection-create','collection-add','collection-remove'}:return self.collection_change(data)
        if action=='save':self.save(data.get('id',''));return self.snapshot()
        if action=='favorite':return self.favorite(data.get('id',''))
        if action=='featured':return self.start_featured(data.get('count',500),data.get('source','both'))
        if action=='starter':return self.start_pack(data.get('count',1000))
        if action=='cancel':self.stop.set();return self.snapshot()
        raise ValueError('Unknown museum action')
