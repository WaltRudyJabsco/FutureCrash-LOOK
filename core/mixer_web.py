"""Authenticated, read-only music discovery for the browser-local Mercury Mix instrument."""
import json
import threading
import time
from pathlib import Path
import urllib.parse
import urllib.request

AUDIO_EXTENSIONS={'.mp3','.m4a','.aac','.flac','.wav','.aiff','.aif','.ogg','.opus','.webm'}
MAX_RESULTS=200
CATALOG_CACHE_SECONDS=20
_CACHE={}
_CACHE_LOCK=threading.Lock()
ASSETS={'mercury-mix-moves.js':'text/javascript; charset=utf-8','mercury-mix-monitor.js':'text/javascript; charset=utf-8','mercury-mix.html':'text/html; charset=utf-8','mercury-mix.css':'text/css; charset=utf-8',
        'mercury-mix.js':'text/javascript; charset=utf-8','mercury-mix-dsp.js':'text/javascript; charset=utf-8',
        'mercury-mix-worklet.js':'text/javascript; charset=utf-8'}


def catalog(data,query="",offset=0):
    if not isinstance(query,str) or len(query)>200:raise ValueError("Search text must be at most 200 characters")
    query=query.casefold()
    rows=[];seen=set()
    for row in data.get('entries',[]):
        if not isinstance(row,dict) or row.get('offline') or row.get('fabric_hidden_by'):continue
        if str(row.get('media_type','')).lower().startswith('video'):continue
        if Path(str(row.get('path',''))).suffix.lower() not in AUDIO_EXTENSIONS:continue
        ident=str(row.get('id') or '');node=str(row.get('node') or '')
        if not ident or (node,ident) in seen:continue
        seen.add((node,ident));tags=row.get('tags') or row.get('metadata') or {}
        if not isinstance(tags,dict):tags={}
        title=row.get('title') or tags.get('title') or Path(str(row.get('path',''))).stem
        stream_query=urllib.parse.urlencode({'node':node,'id':ident})
        rows.append({'id':ident,'node':node,'title':str(title),'artist':str(row.get('artist') or tags.get('artist') or ''),
                     'album':str(row.get('album') or tags.get('album') or ''),'duration':row.get('duration'),'format':Path(str(row.get('path',''))).suffix[1:].upper(),'_rank':0 if row.get('track') or tags.get('track') else 1,
                     'audio_url':'/api/media/browser?'+stream_query,'cover_url':'/api/media/cover?'+stream_query})
    available=len(rows)
    rows=[row for row in rows if query in ' '.join(row.get(k,'') for k in ('artist','title','album','node')).casefold()]
    rows.sort(key=lambda row:(row['_rank'],row['artist'].casefold(),row['title'].casefold()))
    for row in rows:row.pop('_rank')
    return {'entries':rows[offset:offset+MAX_RESULTS],'total':len(rows),'available':available,'offset':offset,'has_more':offset+MAX_RESULTS<len(rows),'truncated':len(rows)>MAX_RESULTS,
            'errors':data.get('errors',[]),'refreshing':bool(data.get('refreshing'))}


def asset(name):
    if name not in ASSETS:raise ValueError('Unknown Mercury Mix asset')
    # Both standalone hosts install the same immutable assets; source checkouts
    # share the Signal copy. No path supplied by a client is opened.
    roots=[Path(__file__).resolve().parent.parent/'signal-window',Path.home()/'.local/share/signal-window',Path.home()/'.local/share/albert']
    for root in roots:
        path=root/name
        if path.is_file():return path.read_bytes()
    raise FileNotFoundError('Mercury Mix assets are missing; update this host')


def handle(handler,node_url):
    path=urllib.parse.urlsplit(handler.path).path
    if path=='/api/mix/library':
        params=urllib.parse.parse_qs(urllib.parse.urlsplit(handler.path).query)
        query=params.get('q',[''])[0];offset=int(params.get('offset',['0'])[0])
        if len(query)>200 or not 0<=offset<=1000000:raise ValueError('Invalid library search')
        with _CACHE_LOCK:
            cached=_CACHE.get(node_url)
            if cached and time.monotonic()-cached[0]<CATALOG_CACHE_SECONDS:data=cached[1]
            else:
                with urllib.request.urlopen(node_url+'/v1/media/fabric',timeout=12) as response:data=json.load(response)
                _CACHE[node_url]=(time.monotonic(),data)
        value=catalog(data,query,offset)
        data=json.dumps(value).encode();content='application/json'
    else:
        name='mercury-mix.html' if path in {'/mix','/mix/'} else path.removeprefix('/mix/assets/')
        if path not in {'/mix','/mix/'} and not path.startswith('/mix/assets/'):raise ValueError('Unknown Mercury Mix route')
        data=asset(name);content=ASSETS[name]
    handler.send_response(200);handler.send_header('Content-Type',content);handler.send_header('Content-Length',str(len(data)))
    handler.send_header('Cache-Control','private, no-store');handler.send_header('X-Content-Type-Options','nosniff')
    handler.send_header('Referrer-Policy','same-origin')
    handler.send_header('Content-Security-Policy',"default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' blob: data:; media-src 'self' blob:; connect-src 'self'; worker-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'self'")
    handler.end_headers();handler.wfile.write(data)
