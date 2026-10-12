"""Disc labels are hints; online movie matches always need a human choice."""
from __future__ import annotations
import json
from pathlib import Path
import re
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

LOOKUP_TIMEOUT_SECONDS=8
LOOKUP_MAX_BYTES=1024*1024
API='https://www.wikidata.org/w/api.php'


def text(value):
    return ''.join(char for char in str(value or '') if ord(char)>=32 and not 127<=ord(char)<160)[:300]


def disc_hint(drive):
    mount=Path(drive['mount']) if drive.get('mount') else None
    kind='';name=drive.get('disc') or (mount.name if mount else '')
    if mount:
        if (mount/'BDMV').is_dir():
            kind='bluray'
            for path in sorted((mount/'BDMV/META/DL').glob('bdmt_*.xml')):
                try:
                    if path.stat().st_size>128*1024:continue
                    root=ET.fromstring(path.read_bytes())
                    names=[node.text for node in root.iter() if node.tag.rsplit('}',1)[-1]=='name' and node.text]
                    if names:name=names[0];break
                except (OSError,ET.ParseError):continue
        elif (mount/'VIDEO_TS').is_dir():kind='dvd'
        else:
            try:
                if any(path.suffix.lower() in {'.aiff','.aif','.aifc'} for path in mount.iterdir()):kind='cd'
            except OSError:pass
    # Remove a manufacturing suffix like PCU43_A, keeping ordinary numeric titles.
    name=re.sub(r'^([A-Z]+)\d+_[A-Z]$',r'\1',text(name))
    name=re.sub(r'[_]+',' ',name).strip()
    return {'kind':kind,'title':name}


def _json(params):
    url=API+'?'+urllib.parse.urlencode(dict(params,format='json',maxlag=5))
    req=urllib.request.Request(url,headers={'User-Agent':'FutureCrash-LOOK/8.16 (disc metadata; https://github.com/WaltRudyJabsco/FutureCrash-LOOK)'})
    with urllib.request.urlopen(req,timeout=LOOKUP_TIMEOUT_SECONDS) as response:
        data=response.read(LOOKUP_MAX_BYTES+1)
    if len(data)>LOOKUP_MAX_BYTES:raise ValueError('Movie lookup response too large')
    result=json.loads(data)
    if not isinstance(result,dict):raise ValueError('Invalid movie lookup response')
    if result.get('error'):raise ValueError('Movie metadata service is temporarily unavailable')
    return result


def movies(query):
    query=text(query).strip()
    if not query:raise ValueError('Enter a movie name to search')
    results=_json({'action':'wbsearchentities','search':query,'language':'en','limit':10}).get('search') or []
    candidates=[row for row in results if isinstance(row,dict) and re.fullmatch(r'Q\d+',str(row.get('id',''))) and
                re.search(r'\b(film|movie|documentary)\b',row.get('description',''),re.I)]
    if not candidates:return {'ok':True,'matches':[],'source':'Wikidata'}
    entities=_json({'action':'wbgetentities','ids':'|'.join(row['id'] for row in candidates),
                    'props':'claims','languages':'en'}).get('entities') or {}
    matches=[]
    for row in candidates:
        dates=[]
        for claim in (entities.get(row['id'],{}).get('claims') or {}).get('P577',[]):
            value=((claim.get('mainsnak') or {}).get('datavalue') or {}).get('value') or {}
            match=re.match(r'^\+(\d{4})-',value.get('time',''))
            if match:dates.append(match[1])
        year=min(dates) if dates else ''
        matches.append({'title':text(row.get('label') or query),'year':year,
                        'description':text(row.get('description')),'source':'https://www.wikidata.org/wiki/'+row['id']})
    return {'ok':True,'matches':matches,'source':'Wikidata'}
