"""Native attention effects, independent of any open Fabric window."""
from __future__ import annotations
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

DEFAULTS={'desktop':True,'sound':True,'voice':False}


def settings_path(): return Path.home()/'.config/look/notifications.json'


def settings(changes=None):
    path=settings_path(); value=dict(DEFAULTS)
    try: value.update({k:v for k,v in json.loads(path.read_text()).items() if k in DEFAULTS and isinstance(v,bool)})
    except (OSError,ValueError,AttributeError): pass
    if changes is not None:
        if not isinstance(changes,dict) or set(changes)-set(DEFAULTS) or any(not isinstance(v,bool) for v in changes.values()):
            raise ValueError('Notification settings are desktop, sound and voice booleans')
        value.update(changes); path.parent.mkdir(parents=True,exist_ok=True)
        fd,temp=tempfile.mkstemp(dir=path.parent,prefix='.notifications-')
        try:
            with os.fdopen(fd,'w') as stream: json.dump(value,stream)
            os.replace(temp,path)
        finally:
            if os.path.exists(temp): os.unlink(temp)
    return value


def deliver(title,message,options=None):
    options=settings() if options is None else options
    receipts=[]; title=str(title)[:200]; message=str(message)[:1200]
    commands=[]
    if sys.platform=='darwin':
        if options.get('desktop') and shutil.which('osascript'):
            script='on run argv\n display notification (item 2 of argv) with title (item 1 of argv) sound name (item 3 of argv)\nend run'
            commands.append(('desktop',['osascript','-e',script,title,message,'Glass' if options.get('sound') else '']))
        elif options.get('sound') and shutil.which('afplay'):
            commands.append(('sound',['afplay','/System/Library/Sounds/Glass.aiff']))
    else:
        if options.get('desktop') and shutil.which('notify-send'):
            commands.append(('desktop',['notify-send','--app-name=Fabric','--',title,message]))
        if options.get('sound') and shutil.which('canberra-gtk-play'):
            commands.append(('sound',['canberra-gtk-play','--id=message-new-instant']))
        elif options.get('sound') and shutil.which('paplay'):
            sound=Path('/usr/share/sounds/freedesktop/stereo/message.oga')
            if sound.exists(): commands.append(('sound',['paplay',str(sound)]))
    for channel,command in commands:
        try:
            result=subprocess.run(command,stdin=subprocess.DEVNULL,capture_output=True,text=True,timeout=4)
            receipts.append({'channel':channel,'ok':result.returncode==0,'detail':result.stderr.strip()[:200]})
        except (OSError,subprocess.SubprocessError) as exc:
            receipts.append({'channel':channel,'ok':False,'detail':str(exc)[:200]})
    return {'ok':any(item['ok'] for item in receipts),'delivery':receipts,
            'settings':options,'detail':'OS delivery requested' if receipts else 'Native notification tools unavailable; Fabric reminder remains visible'}
