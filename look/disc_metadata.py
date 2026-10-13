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
    if item.get('content_kind')=='unclassified':return item['title']
    return ('Special' if item.get('content_kind')=='special' else 'Extra')+' - '+item['title']


def validate_tv_titles(value):
    if not isinstance(value,dict) or len(value)>999:raise ValueError('Invalid TV title mapping')
    for index,item in value.items():
        if not isinstance(index,str) or not index.isdigit() or not isinstance(item,dict):raise ValueError('Invalid TV title mapping')
        for key in ('title','series','source','filename'):
            if key in item and (not isinstance(item[key],str) or len(item[key])>300):raise ValueError('Invalid TV title metadata')
        if not item.get('title') or not item.get('series') or item.get('content_kind') not in {'episode','special','extra','unclassified'}:raise ValueError('Invalid TV title metadata')
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


def series_query(label):
    """Edition and disc suffixes identify the box, not the television series."""
    value=text(label).replace('_',' ').strip()
    value=re.sub(r'\s*[-–:]?\s*(?:special|collector.s|complete|deluxe)\s+edition\b.*$','',value,flags=re.I)
    value=re.sub(r'\s*[-–:]?\s*(?:disc|disk|dvd|blu[ -]?ray|season|series)\s*\d+.*$','',value,flags=re.I)
    value=re.sub(r'\s+(?:dvd|blu[ -]?ray|box\s*set)\s*$','',value,flags=re.I)
    return value.strip(' -:') or text(label)


def discogs_reference(value):
    raw=str(value or '').strip()
    match=re.fullmatch(r'\[?([rm]?)(\d+)\]?',raw,re.I)
    if match:kind='masters' if match[1].lower()=='m' else 'releases';identifier=int(match[2])
    else:
        parsed=urllib.parse.urlparse(raw)
        if parsed.scheme!='https' or parsed.hostname not in {'discogs.com','www.discogs.com'} or parsed.username or parsed.port:raise ValueError('Enter a Discogs link, r-number, m-number or release ID')
        match=re.match(r'^/(?:[a-z]{2}/)?(release|master)/(\d+)(?:-|/|$)',parsed.path)
        if not match:raise ValueError('Choose a Discogs release or master link')
        kind='masters' if match[1]=='master' else 'releases';identifier=int(match[2])
    if not 0<identifier<10**10:raise ValueError('Invalid Discogs ID')
    return kind,identifier


def discogs_id(value):
    kind,identifier=discogs_reference(value)
    if kind!='releases':raise ValueError('Choose an edition from this master first')
    return identifier


def _discogs_json(identifier,resource='releases'):
    request=urllib.request.Request('https://api.discogs.com/'+resource+'/'+str(identifier),
        headers={'User-Agent':'FutureCrash-LOOK/8.16 (reviewed disc metadata; https://github.com/WaltRudyJabsco/FutureCrash-LOOK)'})
    with urllib.request.urlopen(request,timeout=LOOKUP_TIMEOUT_SECONDS) as response:
        data=response.read(LOOKUP_MAX_BYTES+1)
    if len(data)>LOOKUP_MAX_BYTES:raise ValueError('Discogs response too large')
    result=json.loads(data)
    if not isinstance(result,dict):raise ValueError('Invalid Discogs response')
    return result


def discogs_release(value):
    identifier=discogs_id(value);data=_discogs_json(identifier)
    source='https://www.discogs.com/release/'+str(identifier)
    tracks=[]
    def collect(items,heading='',depth=0):
        if not isinstance(items,list) or depth>4:raise ValueError('Invalid Discogs contents nesting')
        for row in items[:1000]:
            if not isinstance(row,dict):continue
            if row.get('type_')=='heading':heading=text(row.get('title'));continue
            title=text(row.get('title'));position=text(row.get('position'))
            if row.get('sub_tracks'):collect(row['sub_tracks'],title or heading,depth+1)
            elif title:tracks.append({'title':title,'position':position,'heading':heading,
                                      'duration':text(row.get('duration')),'source':source,
                                      'content_kind':'unclassified'})
    collect(data.get('tracklist') or [])
    artist=text(' / '.join(row.get('name','') for row in data.get('artists',[]) if isinstance(row,dict)))
    return {'ok':True,'release':{'id':identifier,'title':text(data.get('title')),'artist':artist,
            'year':text(data.get('year')),'country':text(data.get('country')),'source':source,
            'formats':text(' / '.join(str(item.get('qty') or '')+' '+str(item.get('name') or '')+' '+', '.join(item.get('descriptions') or []) for item in data.get('formats',[]) if isinstance(item,dict))),
            'tracks':tracks[:1000]},'source':'Discogs'}


def discogs_lookup(value):
    kind,identifier=discogs_reference(value)
    if kind=='releases':
        try:return discogs_release(str(identifier))
        except urllib.error.HTTPError as exc:
            if exc.code!=404 or not str(value).strip().isdigit():raise
            kind='masters'  # Bare spoken numbers may identify a master; editions still require confirmation.
    master=_discogs_json(identifier,'masters')
    # Exact editions differ in country, video standard and sometimes contents.
    versions=_discogs_json(str(identifier)+'/versions?per_page=100','masters')
    editions=[]
    for item in (versions.get('versions') or [])[:100]:
        if not isinstance(item,dict) or type(item.get('id')) is not int:continue
        editions.append({'id':item['id'],'title':text(item.get('title')),'country':text(item.get('country')),
                         'year':text(item.get('released')),'format':text(item.get('format'))})
    return {'ok':True,'master':{'title':text(master.get('title')),'id':identifier},'editions':editions,
            'more_editions':int((versions.get('pagination') or {}).get('items') or 0)>100,'source':'Discogs'}


DURATION_MATCH_TOLERANCE_SECONDS=2


def duration_seconds(value):
    if not re.fullmatch(r'\d+(?::\d{1,2}){1,2}',str(value or '')):return None
    parts=[int(part) for part in value.split(':')]
    if any(part>=60 for part in parts[1:]):return None
    total=0
    for part in parts:total=total*60+part
    return total or None


def duration_suggestion(title,candidates):
    seconds=duration_seconds(title.get('duration'))
    if seconds is None:return None
    matches=[index for index,item in enumerate(candidates,1)
             if (duration:=duration_seconds(item.get('duration'))) is not None
             and abs(seconds-duration)<=DURATION_MATCH_TOLERANCE_SECONDS]
    return str(matches[0]) if len(matches)==1 else None
