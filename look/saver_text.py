"""Explicit Fabric-generated fiction, cached locally; rendering never calls AI."""
from functools import lru_cache
import json
from pathlib import Path
import re
import sys

import book_reader

MAX_BYTES=16384
MAX_PHRASES=12
MAX_LENGTH=48


def path():return Path.home()/'.config/look/saver-text.json'


def phrases(value):
    if not isinstance(value,list):return []
    result=[]
    for item in value[:MAX_PHRASES]:
        if not isinstance(item,str):continue
        text=' '.join(item.strip().upper().split())
        if 3<=len(text)<=MAX_LENGTH and re.fullmatch(r'[A-Z0-9][A-Z0-9 .,:!?/\-]*',text) and text not in result:result.append(text)
    return result


@lru_cache(maxsize=1)
def read():
    try:
        with path().open('rb') as source:raw=source.read(MAX_BYTES+1)
        if len(raw)>MAX_BYTES:return ()
        value=json.loads(raw)
        if not isinstance(value,dict):return ()
        return tuple(phrases(value.get('phrases')))
    except (OSError,ValueError):return ()


def generate():
    candidates=[Path(__file__).resolve().parents[1]/'core',Path.home()/'.local/share/future-crash-look/core']
    for folder in candidates:
        if (folder/'fabric_client.py').is_file():
            sys.path.insert(0,str(folder));break
    import fabric_client
    print('Preparing fictional Flight Deck phrases through Fabric…',flush=True)
    result=fabric_client.infer([
        {'role':'system','content':'Write original, atmospheric fictional spacecraft-computer captions. No real alerts, personal data, commands, or claims about this computer. Return only 12 short uppercase lines, each 3 to 48 characters. No bullets or markup.'},
        {'role':'user','content':'Quiet deep-space watch, distant signals, dreamlike navigation. Brief, poetic, restrained.'}],
        owner='look-saver-text',priority='background',latency=True,think=False,
        options={'num_predict':220,'temperature':.8},timeout=45)
    message=result.get('message') or {}
    text=message.get('content','') if isinstance(message,dict) else ''
    accepted=phrases(str(text).splitlines())
    if len(accepted)<3:raise ValueError('AI returned too few usable captions; existing text is unchanged')
    book_reader.write_json(path(),{'schema':1,'phrases':accepted})
    read.cache_clear()
    print(f'Saved {len(accepted)} fictional captions · new visualizer/saver sessions use them offline')
    return 0


def reset():
    path().unlink(missing_ok=True);read.cache_clear()
    print('Flight Deck uses built-in captions on the next launch');return 0
