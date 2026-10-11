"""Audio outputs use the host audio service; discovery never chooses a speaker."""
from __future__ import annotations
import concurrent.futures
import hashlib
import socket
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile

MAX_OUTPUTS = 128
DISCOVERY_SECONDS = 2


def clean(value): return ''.join(c for c in str(value) if c.isprintable())[:180]
def config_path(): return Path.home()/'.config/look/media_output.json'
def read():
    try:
        value=json.loads(config_path().read_text())
        return value if isinstance(value,dict) else {}
    except (OSError,ValueError): return {}


def save(value):
    path=config_path();path.parent.mkdir(parents=True,exist_ok=True)
    fd,tmp=tempfile.mkstemp(dir=path.parent)
    try:
        with os.fdopen(fd,'w') as out:json.dump(value,out);out.write('\n')
        os.replace(tmp,path)
    finally:
        if os.path.exists(tmp):os.unlink(tmp)


def mpv_binary():
    try:
        from . import media_open
    except ImportError:
        import media_open
    return media_open.mpv_binary()


def audio_devices(text):
    rows=[];seen=set()
    preferred='pipewire/' if "'pipewire/" in text else ('pulse/' if "'pulse/" in text else None)
    for line in text.splitlines():
        match=re.match(r"\s*'([^'\r\n]+)'\s+\((.*)\)\s*$",line)
        if not match:continue
        device,label=match.groups()
        if device=='auto' or '/' not in device:continue
        # Prefer the host's native backend over duplicate compatibility backends.
        if sys.platform=='darwin' and not device.startswith('coreaudio/'):continue
        if sys.platform.startswith('linux') and device.startswith('pulse/') and any(r['device']==device.replace('pulse/','pipewire/',1) for r in rows):continue
        if sys.platform.startswith('linux') and preferred and not device.startswith(preferred):continue
        if device in seen:continue
        seen.add(device)
        raop=re.search(r'raop_sink\.(.+?\.local)\.',device)
        stable='raop/'+raop.group(1) if raop else device
        rows.append({'output_id':'audio-'+hashlib.sha256(stable.encode()).hexdigest()[:20],
                     'device':device,'label':clean(label),'kind':'airplay' if 'raop_sink.' in device else 'audio',
                     'available':True,'capabilities':['media.audio'],'reason':''})
    return rows[:MAX_OUTPUTS]


def native():
    mpv=mpv_binary()
    if not mpv:return []
    result=subprocess.run([mpv,'--no-config','--audio-device=help'],capture_output=True,text=True,timeout=5)
    if result.returncode:raise ValueError('Could not enumerate audio outputs: '+clean(result.stderr))
    return audio_devices(result.stdout)


def airplay():
    """Bounded Bonjour browse on Macs; Linux receivers arrive as native RAOP sinks."""
    binary=shutil.which('dns-sd')
    if sys.platform!='darwin' or not binary:return []
    process=subprocess.Popen([binary,'-B','_raop._tcp','local.'],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
    try:
        try:out,_=process.communicate(timeout=DISCOVERY_SECONDS)
        except subprocess.TimeoutExpired:
            process.terminate()
            try:out,_=process.communicate(timeout=1)
            except subprocess.TimeoutExpired:process.kill();out,_=process.communicate()
    finally:
        if process.poll() is None:process.kill();process.wait()
    devices={}
    for line in out.splitlines():
        match=re.search(r'\b(Add|Rmv)\s+\d+\s+\d+\s+local\.\s+_raop\._tcp\.\s+(.+)$',line)
        if not match:continue
        action,name=match.groups()
        if action=='Rmv':devices.pop(name,None);continue
        label=name.split('@',1)[-1]
        devices[name]={'output_id':'airplay-'+hashlib.sha256(name.encode()).hexdigest()[:20],
                       'label':clean(label),'kind':'airplay','available':False,'capabilities':['media.audio'],
                       'reason':'Found on the network. Connect in macOS Sound settings and refresh, or use a Linux AirPlay bridge.'}
    return list(devices.values())[:MAX_OUTPUTS]


def receiver_ready(row):
    match=re.search(r'raop_sink\..+\.((?:\d{1,3}\.){3}\d{1,3})(?:%[^.]+)?\.(\d+)$',row.get('device',''))
    if not match:return True
    try:
        with socket.create_connection((match.group(1),int(match.group(2))),timeout=.5):return True
    except OSError:return False


def catalog(discover=False):
    rows=native();selected=read().get('output_id','default')
    receivers=[r for r in rows if r.get('kind')=='airplay']
    with concurrent.futures.ThreadPoolExecutor(max_workers=16) as pool:
        for row,ready in zip(receivers,pool.map(receiver_ready,receivers)):
            if not ready:
                row['available']=False
                row['reason']='Receiver discovered, but its AirPlay address is unreachable from this bridge. Check the local network or connect through another node.'
    if discover:
        names={r['label'].casefold() for r in rows}
        rows.extend(r for r in airplay() if r['label'].casefold() not in names)
    if selected!='default' and not any(r['output_id']==selected for r in rows):
        rows.append({'output_id':selected,'label':clean(read().get('label') or 'Selected speaker'),'kind':'audio','available':False,'capabilities':['media.audio'],'reason':'Selected output disconnected; no automatic fallback.'})
    for row in rows:row['selected']=row['output_id']==selected
    return rows[:MAX_OUTPUTS]


def selected_device():
    selected=read().get('output_id','default')
    if selected=='default':return 'auto'
    row=next((r for r in native() if r['output_id']==selected),None)
    if row is None:raise ValueError('Selected speaker is disconnected. Open lk media outputs and explicitly choose another output.')
    if not receiver_ready(row):raise ValueError('Selected AirPlay receiver is unreachable from this bridge; no fallback output was chosen')
    return row['device']


def select(output_id, request=None):
    if output_id=='default':row={'output_id':'default','device':'auto','label':'System default'}
    else:
        row=next((r for r in native() if r['output_id']==output_id),None)
        if row is None:raise ValueError('Output is not ready. Connect it in the host sound settings or enable Linux AirPlay, then refresh.')
    if not receiver_ready(row):raise ValueError('AirPlay receiver is unreachable from this bridge. Check the local network; selection was not changed')
    previous=read()
    if request:
        result=request(['set_property','audio-device',row['device']])
        if not result or result.get('error')!='success':raise ValueError('Player rejected this output; selection was not saved')
        actual=request(['get_property','audio-device'])
        if not actual or actual.get('data')!=row['device']:
            request(['set_property','audio-device',previous.get('device','auto')])
            raise ValueError('Player did not confirm the selected output')
    save({k:row[k] for k in ('output_id','device','label')})
    return {'ok':True,'output_id':output_id,'label':row['label'],'message':'Selected '+row['label']}


def enable_airplay():
    if not sys.platform.startswith('linux'):raise ValueError('On a Mac, connect AirPlay in Sound settings. Bluetooth pairing also belongs to the host settings.')
    pactl='/usr/bin/pactl' if Path('/usr/bin/pactl').is_file() else shutil.which('pactl')
    if not pactl:raise ValueError('Install/configure PipeWire with its PulseAudio interface first')
    def run(args):
        result=subprocess.run([pactl,*args],capture_output=True,text=True,timeout=8)
        if result.returncode:raise ValueError(clean(result.stderr) or 'Audio service unavailable')
        return result.stdout.strip()
    original=run(['get-default-sink'])
    try:
        if 'module-raop-discover' not in run(['list','short','modules']):run(['load-module','module-raop-discover'])
    finally:
        if original and run(['get-default-sink'])!=original:run(['set-default-sink',original])
    return {'ok':True,'message':'AirPlay discovery enabled for this audio-service session. Refresh outputs in a few seconds; the existing default was preserved.'}
