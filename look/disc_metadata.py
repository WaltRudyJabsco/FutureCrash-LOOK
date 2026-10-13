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


def _tv_json(route):
    request=urllib.request.Request('https://api.tvmaze.com'+route,
        headers={'User-Agent':'FutureCrash-LOOK/8.16 (TV disc metadata)'})
    with urllib.request.urlopen(request,timeout=LOOKUP_TIMEOUT_SECONDS) as response:
        data=response.read(LOOKUP_MAX_BYTES+1)
    if len(data)>LOOKUP_MAX_BYTES:raise ValueError('TV metadata response too large')
    return json.loads(data)


def tv_search(query):
    query=text(query).strip()
    if not query:raise ValueError('Enter a series name')
    rows=_tv_json('/search/shows?'+urllib.parse.urlencode({'q':query}))
    if not isinstance(rows,list):raise ValueError('Invalid TV metadata response')
    matches=[]
    for row in rows[:10]:
        show=row.get('show') if isinstance(row,dict) else None
        if not isinstance(show,dict) or type(show.get('id')) is not int:continue
        matches.append({'id':show['id'],'title':text(show.get('name')),
                        'year':text(show.get('premiered'))[:4],
                        'source':'https://www.tvmaze.com/shows/'+str(show['id'])})
    return {'ok':True,'matches':matches,'source':'TVmaze'}


def tv_episodes(identifier):
    if type(identifier) is not int or identifier<=0:raise ValueError('Choose a valid series')
    rows=_tv_json('/shows/'+str(identifier)+'/episodes?specials=1')
    if not isinstance(rows,list):raise ValueError('Invalid episode response')
    episodes=[]
    for row in rows[:2000]:
        if not isinstance(row,dict) or type(row.get('id')) is not int:continue
        season=row.get('season');number=row.get('number')
        if type(season) is not int or season<0:continue
        if number is not None and (type(number) is not int or number<1):continue
        episodes.append({'title':text(row.get('name')),'season':season,'episode':number,
                         'content_kind':'special' if number is None else 'episode',
                         'runtime':row.get('runtime') if type(row.get('runtime')) is int else None,
                         'source':'https://www.tvmaze.com/episodes/'+str(row['id'])})
    return {'ok':True,'episodes':episodes,'source':'TVmaze'}


def episode_label(item):
    if item.get('content_kind')=='episode':
        return f"S{item['season']:02d}E{item['episode']:02d} - {item['title']}"
    return ('Special' if item.get('content_kind')=='special' else 'Extra')+' - '+item['title']


def validate_tv_titles(value):
    if not isinstance(value,dict) or len(value)>999:raise ValueError('Invalid TV title mapping')
    for index,item in value.items():
        if not isinstance(index,str) or not index.isdigit() or not isinstance(item,dict):raise ValueError('Invalid TV title mapping')
        for key in ('title','series','source','filename'):
            if key in item and (not isinstance(item[key],str) or len(item[key])>300):raise ValueError('Invalid TV title metadata')
        if not item.get('title') or not item.get('series') or item.get('content_kind') not in {'episode','special','extra'}:raise ValueError('Invalid TV title metadata')
        for key in ('season','episode'):
            if item.get(key) is not None and (type(item[key]) is not int or not 0<=item[key]<=999):raise ValueError('Invalid episode number')
        filename=item.get('filename','')
        if filename and (Path(filename).name!=filename or '/' in filename or '\\' in filename or filename in {'.','..'}):raise ValueError('Invalid disc filename')
        if item['content_kind']=='episode' and (item.get('season') is None or not item.get('episode')):raise ValueError('Episode needs season and number')
    return value


def _music_json(route):
    request=urllib.request.Request('https://musicbrainz.org/ws/2/'+route,
        headers={'User-Agent':'FutureCrash-LOOK/8.16 (manual CD barcode lookup)'})
    with urllib.request.urlopen(request,timeout=LOOKUP_TIMEOUT_SECONDS) as response:
        data=response.read(LOOKUP_MAX_BYTES+1)
    if len(data)>LOOKUP_MAX_BYTES:raise ValueError('CD metadata response too large')
    result=json.loads(data)
    if not isinstance(result,dict):raise ValueError('Invalid CD metadata response')
    return result


def cd_barcode(value):
    barcode=re.sub(r'[ -]','',str(value or ''))
    if not re.fullmatch(r'\d{8}|\d{12,14}',barcode):raise ValueError('Enter 8, 12, 13 or 14 barcode digits')
    rows=_music_json('release?'+urllib.parse.urlencode({'query':'barcode:'+barcode,'fmt':'json','limit':10})).get('releases') or []
    releases=[]
    for row in rows:
        if not isinstance(row,dict) or row.get('barcode')!=barcode:continue
        releases.append({'title':text(row.get('title')),'release_id':row.get('id'),
                         'artist':text(''.join(item.get('name','')+item.get('joinphrase','') for item in row.get('artist-credit',[]) if isinstance(item,dict))),
                         'date':text(row.get('date')),'country':text(row.get('country'))})
    return {'ok':True,'releases':releases,'source':'MusicBrainz'}


def cd_release(identifier):
    import uuid
    identifier=str(uuid.UUID(str(identifier)))
    data=_music_json('release/'+identifier+'?'+urllib.parse.urlencode({'inc':'artists+recordings','fmt':'json'}))
    artist=text(''.join(item.get('name','')+item.get('joinphrase','') for item in data.get('artist-credit',[]) if isinstance(item,dict)))
    releases=[]
    for medium in data.get('media') or []:
        tracks=medium.get('tracks') or []
        if not tracks:continue
        releases.append({'title':text(data.get('title')),'artist':artist,'release_id':identifier,
                         'disc':medium.get('position'),
                         'tracks':[text(track.get('title') or (track.get('recording') or {}).get('title')) for track in tracks]})
    return {'ok':True,'releases':releases,'source':'MusicBrainz'}
