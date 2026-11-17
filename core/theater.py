"""Expiring media admission and a shared playback clock for Fabric Theater."""
from __future__ import annotations
import hashlib
from contextlib import contextmanager
import json
import math
import os
from pathlib import Path
import secrets
import sqlite3
import threading
import time
import urllib.parse
import urllib.request

PORT = 7340
MAX_LIFETIME_HOURS = 720
COOKIE = 'fabric_theater'


def root():
    return Path.home()/'.local/share/future-crash-look/theater'


@contextmanager
def connect():
    directory=root();directory.mkdir(parents=True,exist_ok=True,mode=0o700)
    db=sqlite3.connect(directory/'theater.sqlite3',timeout=10)
    db.row_factory=sqlite3.Row
    db.executescript('''CREATE TABLE IF NOT EXISTS tickets
      (id TEXT PRIMARY KEY, digest TEXT UNIQUE, scope TEXT, media TEXT, title TEXT, expires REAL, revoked INTEGER DEFAULT 0);
      CREATE TABLE IF NOT EXISTS settings (id INTEGER PRIMARY KEY, value TEXT);
      CREATE TABLE IF NOT EXISTS channel (id INTEGER PRIMARY KEY, value TEXT);''')
    os.chmod(directory/'theater.sqlite3',0o600)
    try:
        with db:
            yield db
    finally:
        db.close()


def read(table):
    with connect() as db:
        row=db.execute(f'SELECT value FROM {table} WHERE id=1').fetchone()
    return json.loads(row[0]) if row else {}


def write(table,value):
    with connect() as db:
        db.execute(f'INSERT OR REPLACE INTO {table} VALUES (1,?)',(json.dumps(value),))
    return value


def digest(value):
    return hashlib.sha256(value.encode()).hexdigest()


def lifetime(value):
    hours=float(value)
    if not math.isfinite(hours) or not 0<hours<=MAX_LIFETIME_HOURS:
        raise ValueError('Ticket lifetime must be between zero and 720 hours')
    return hours*3600


def configure(url):
    if any(ord(c)<33 for c in url):raise ValueError('Invalid Theater address')
    parsed=urllib.parse.urlsplit(url)
    if parsed.scheme!='https' or not parsed.hostname or parsed.username or parsed.password or parsed.query or parsed.fragment or parsed.path not in {'','/'}:
        raise ValueError('Use the Theater HTTPS origin, for example https://HOST:8443')
    settings=write('settings',{'enabled':True,'url':url.rstrip('/')})
    start_guest()
    return settings


def issue(media=None,title='',scope='movie',hours=24):
    settings=read('settings')
    if not settings.get('enabled'):raise ValueError('Set up Theater on this media host first')
    if scope not in {'movie','channel'} or scope=='movie' and not media:raise ValueError('Choose a movie or channel ticket')
    # Twelve unambiguous characters make a printable code as well as a bearer link.
    code=''.join(secrets.choice('ABCDEFGHJKLMNPQRSTUVWXYZ23456789') for _ in range(12))
    ident=secrets.token_hex(8);expires=time.time()+lifetime(hours)
    with connect() as db:
        db.execute('INSERT INTO tickets VALUES (?,?,?,?,?,?,0)',(ident,digest(code),scope,media or '',title[:300],expires))
    return {'id':ident,'code':code,'url':settings['url']+'/#'+code,'expires':expires,'scope':scope,'title':title}


def admission(code):
    if not isinstance(code,str) or len(code)!=12:raise ValueError('Enter a valid Theater ticket')
    with connect() as db:
        row=db.execute('SELECT * FROM tickets WHERE digest=?',(digest(code.upper()),)).fetchone()
    if row is None or row['revoked'] or row['expires']<=time.time():raise ValueError('Ticket expired, revoked, or unknown')
    return dict(row)


def listing():
    with connect() as db:
        rows=db.execute('SELECT id,scope,title,expires,revoked FROM tickets ORDER BY expires DESC LIMIT 200').fetchall()
    return {'tickets':[dict(r) for r in rows],'channel':channel_state(),'settings':read('settings')}


def revoke(ident):
    with connect() as db:
        if not db.execute('UPDATE tickets SET revoked=1 WHERE id=?',(ident,)).rowcount:raise ValueError('Unknown ticket ID')
    return {'revoked':ident}


def channel_state():
    value=read('channel')
    if not value:return {'state':'stopped','position':0}
    value['position']=value.get('position',0)+(max(0,time.time()-value['updated']) if value['state']=='playing' else 0)
    return value


def control(action,media=None,title='',position=None,public=None):
    # Serialize read/modify/write so two operator requests do not lose a clock update.
    with _CHANNEL_LOCK:
        value=channel_state()
        if action=='show':value={'media':media,'title':title[:300],'state':'playing','position':0,'public':False}
        elif action in {'pause','resume'}:
            if not value.get('media'):raise ValueError('Choose a showing first')
            value['state']='paused' if action=='pause' else 'playing'
        elif action=='stop':value={'state':'stopped','position':0,'public':False}
        elif action=='seek':
            if not value.get('media'):raise ValueError('Choose a showing first')
            position=float(position)
            if not math.isfinite(position) or not 0<=position<=86400:raise ValueError('Invalid playback position')
            value['position']=position
        elif action=='access':
            if type(public) is not bool:raise ValueError('public must be boolean')
            value['public']=public
        else:raise ValueError('Unknown channel control')
        value['updated']=time.time()
        return write('channel',value)


def view(code=None):
    if code:
        ticket=admission(code)
        if ticket['scope']=='movie':return {'mode':'movie','media':ticket['media'],'title':ticket['title'],'expires':ticket['expires']}
    else:
        if not channel_state().get('public'):raise ValueError('Enter a ticket to join Theater')
    return dict(channel_state(),mode='channel')


def media_request(media,range_header=None,head=False):
    # Admission supplies an immutable catalog ID. Guests cannot supply node/path URLs.
    query=urllib.parse.urlencode({'id':media})
    headers={'Range':range_header} if range_header else {}
    return urllib.request.urlopen(urllib.request.Request('http://127.0.0.1:7332/v1/media/browser?'+query,headers=headers,method='HEAD' if head else 'GET'),timeout=120)


_CHANNEL_LOCK=threading.Lock()
_SERVER_LOCK=threading.Lock()
_SERVER=None


def start_guest():
    global _SERVER
    with _SERVER_LOCK:
        if _SERVER is not None:return
        from http.server import ThreadingHTTPServer
        try:from .theater_web import Guest
        except ImportError:from theater_web import Guest
        server=ThreadingHTTPServer(('127.0.0.1',PORT),Guest)
        server.daemon_threads=True
        _SERVER=server
        threading.Thread(target=server.serve_forever,daemon=True,name='fabric-theater').start()


def boot():
    if read('settings').get('enabled'):start_guest()


def admin(payload,catalog,entry):
    action=payload.get('action','status')
    if action=='status':return listing()
    if action=='search':
        query=str(payload.get('query','')).casefold().split()
        rows=catalog().get('entries',[])
        rows=[r for r in rows if str(r.get('media_type','')).startswith(('video/','audio/')) and all(w in (' '.join(str(r.get(k,'')) for k in ('title','artist','album','path'))).casefold() for w in query)]
        return {'items':[{k:r.get(k,'') for k in ('id','title','artist','media_type')} for r in rows[:100]]}
    if action=='configure':return configure(str(payload.get('url','')))
    if action=='ticket':
        scope=payload.get('scope','movie');media=None;title='Theater channel'
        if scope=='movie':
            row,_=entry(str(payload.get('media','')));media=row['id'];title=row.get('title') or 'Untitled'
        return issue(media,title,scope,payload.get('hours',24))
    if action=='qr':
        import base64
        return {'png':base64.b64encode(qr_png(str(payload.get('code','')))).decode()}
    if action=='revoke':return revoke(str(payload.get('id','')))
    if action=='show':
        row,_=entry(str(payload.get('media','')))
        return control('show',row['id'],row.get('title') or 'Untitled')
    return control(action,position=payload.get('position'),public=payload.get('public'))


def qr_png(code):
    import sys
    import io
    path=Path.home()/'.local/share/future-crash-look/theater-python'
    if path.is_dir() and str(path) not in sys.path:sys.path.append(str(path))
    try:import qrcode
    except ImportError as exc:raise ValueError('Install Theater QR support with lk theater qr-setup on this host') from exc
    admission(code)
    url=read('settings')['url']+'/#'+code
    image=qrcode.make(url,box_size=8,border=4)
    output=io.BytesIO();image.save(output,format='PNG')
    return output.getvalue()
