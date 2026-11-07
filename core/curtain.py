"""Paired-node ambient PIN curtain. Not an OS lock or security boundary."""
from pathlib import Path
import concurrent.futures
import hashlib
import hmac
import json
import os
import re
import subprocess
import threading
import time
import uuid

GUARD=threading.RLock()
FAIL_LIMIT=5
COOLDOWN=30
PIN_KDF="pbkdf2-sha256"
PIN_ITERATIONS=600000
PROCESS=None


def path():return Path.home()/'.config/look/curtain.json'


def load():
    try:return json.loads(path().read_text())
    except FileNotFoundError:return {'revision':0,'origin':'','locked':False}


def save(state):
    target=path();target.parent.mkdir(parents=True,exist_ok=True)
    temporary=target.with_name('.curtain-'+uuid.uuid4().hex)
    fd=os.open(temporary,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
    with os.fdopen(fd,'w') as stream:json.dump(state,stream)
    os.replace(temporary,target)


def pin_hash(pin,salt,kdf=PIN_KDF):
    if not isinstance(pin,str) or not re.fullmatch(r'[0-9]{4}',pin):raise ValueError('Enter a four-digit PIN')
    if kdf==PIN_KDF:return hashlib.pbkdf2_hmac('sha256',pin.encode(),bytes.fromhex(salt),PIN_ITERATIONS,dklen=64).hex()
    if kdf=='scrypt':
        if not hasattr(hashlib,'scrypt'):raise RuntimeError('This Python cannot verify the older PIN format; change the PIN from an updated node with scrypt support')
        return hashlib.scrypt(pin.encode(),salt=bytes.fromhex(salt),n=16384,r=8,p=1).hex()
    raise ValueError('Unsupported PIN format')


def verify(state,pin):
    now=time.time()
    if state.get('retry_after',0)>now:raise ValueError('Too many attempts; try again in 30 seconds')
    try:valid=hmac.compare_digest(pin_hash(pin,state['salt'],state.get('kdf','scrypt')),state['verifier'])
    except (ValueError,KeyError):valid=False
    if not valid:
        state['failures']=state.get('failures',0)+1
        if state['failures']>=FAIL_LIMIT:state.update(failures=0,retry_after=now+COOLDOWN)
        save(state);raise ValueError('Incorrect PIN')
    state.update(failures=0,retry_after=0)


def public(state=None):
    state=load() if state is None else state
    return {'configured':bool(state.get('verifier')),'locked':state.get('locked',False),
            'revision':state.get('revision',0),'origin':state.get('origin',''),
            'captions':state.get('captions',[]),'variant':state.get('variant','standard'),
            'notice':'Ambient PIN curtain; not an operating-system lock'}


def desktop():
    """Start only in an existing user desktop; never invent a display/session."""
    global PROCESS
    if PROCESS is not None and PROCESS.poll() is None:return 'running'
    environment=os.environ.copy()
    if os.sys.platform.startswith('linux') and not (environment.get('DISPLAY') or environment.get('WAYLAND_DISPLAY')):
        # The user service manager may know the logged-in desktop's environment.
        result=subprocess.run(['systemctl','--user','show-environment'],capture_output=True,text=True,timeout=3)
        for line in result.stdout.splitlines():
            key,_,value=line.partition('=')
            if key in {'DISPLAY','WAYLAND_DISPLAY','XDG_RUNTIME_DIR','XAUTHORITY','DBUS_SESSION_BUS_ADDRESS'}:environment[key]=value
        if not (environment.get('DISPLAY') or environment.get('WAYLAND_DISPLAY')):
            return 'unavailable: no graphical desktop session'
    root=Path.home()/'.local/share/look';python=root/'saver-runtime/bin/python'
    if not python.is_file() or not (root/'curtain_gui.py').is_file():return 'unavailable: install saver graphics first'
    log=root/'curtain.log'
    with log.open('ab') as stream:
        PROCESS=subprocess.Popen([str(python),str(root/'curtain_gui.py')],stdin=subprocess.DEVNULL,stdout=stream,stderr=stream,start_new_session=True,env=environment)
    return 'launch requested'


def apply(event):
    if not isinstance(event,dict):raise ValueError('Invalid curtain event')
    revision=event.get('revision');origin=event.get('origin')
    if type(revision) is not int or not 0<revision<=time.time_ns()+60_000_000_000:raise ValueError('Invalid revision')
    if not isinstance(origin,str) or not 0<len(origin)<=128:raise ValueError('Invalid origin')
    if type(event.get('locked')) is not bool:raise ValueError('Invalid curtain state')
    for key,length in [('salt',32),('verifier',128)]:
        if not isinstance(event.get(key),str) or not re.fullmatch('[0-9a-f]{'+str(length)+'}',event[key]):raise ValueError('Invalid PIN verifier')
    kdf=event.get('kdf','scrypt')
    if kdf not in {PIN_KDF,'scrypt'}:raise ValueError('Unsupported PIN format')
    variant=event.get('variant','standard')
    if variant not in {'standard','they-live','gypsy'}:raise ValueError('Invalid curtain variant')
    with GUARD:
        state=load()
        if (revision,origin)<=(state.get('revision',0),state.get('origin','')):return {'ok':True,'stale':True,**public(state)}
        attempts={key:state.get(key,0) for key in ('failures','retry_after')} if state.get('verifier')==event['verifier'] else {}
        state={key:event[key] for key in ('revision','origin','locked','salt','verifier')}
        captions=event.get('captions',[])
        if not isinstance(captions,list) or len(captions)>12 or any(not isinstance(text,str) or len(text)>48 or not re.fullmatch(r'[A-Z0-9 .,:!?/\-]+',text) for text in captions):raise ValueError('Invalid captions')
        state.update(attempts,captions=captions,kdf=kdf,variant=variant)
        save(state)
        result={'ok':True,**public(state)}
        if state['locked']:
            try:result['desktop']=desktop()
            except (OSError,subprocess.SubprocessError) as exc:result['desktop']='unavailable: '+str(exc)
        return result


def operate(data,origin,peers,send):
    action=data.get('action','status')
    if action=='status':return {'ok':True,**public()}
    if action=='receive':return apply(data.get('event'))
    if action not in {'setup','lock','unlock'}:raise ValueError('Use setup, lock, unlock or status')
    with GUARD:
        state=load()
        if action=='setup':
            if state.get('locked'):raise ValueError('Unlock before changing the PIN')
            if state.get('verifier'):verify(state,data.get('old_pin'))
            salt=os.urandom(16).hex();state.update(salt=salt,verifier=pin_hash(data.get('pin'),salt),kdf=PIN_KDF)
        elif not state.get('verifier'):raise ValueError('Set a PIN first: lk lock setup')
        elif action=='unlock':
            verify(state,data.get('pin'));save(state)
        event={key:state[key] for key in ('salt','verifier')}
        event.update(variant=data.get('variant','standard') if action=='lock' else state.get('variant','standard'),kdf=state.get('kdf','scrypt'),revision=max(time.time_ns(),state.get('revision',0)+1),origin=origin,locked=action=='lock',captions=data.get('captions',state.get('captions',[])))
        local=apply(event)
    def deliver(peer):
        try:return {'node':peer,**send(peer,{'action':'receive','event':event})}
        except Exception:return {'node':peer,'ok':False,'error':'Unreachable or curtain unavailable; retry when online'}
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:deliveries=list(pool.map(deliver,peers))
    deliveries.insert(0,{'node':origin,**local})
    return {'ok':all(item.get('ok') for item in deliveries),**public(),'delivery':deliveries}
