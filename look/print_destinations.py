"""Physical printer identity and route choice, independent of CUPS/UI I/O."""
import hashlib
import re
from urllib.parse import urlsplit,parse_qs,unquote


def endpoint(uri):
    try:
        parsed=urlsplit(uri)
        if parsed.scheme not in {'ipp','ipps','socket','lpd','usb'} or not parsed.hostname:return ''
        # IPP and IPPS can describe the same resource. Preserve resource paths:
        # a shared print server may expose many printers on the same host.
        scheme='ipp' if parsed.scheme in {'ipp','ipps'} else parsed.scheme
        port=parsed.port or (631 if scheme=='ipp' else 9100 if scheme=='socket' else 515 if scheme=='lpd' else 0)
        return scheme+'://'+parsed.hostname.casefold().rstrip('.')+':'+str(port)+unquote(parsed.path).rstrip('/')+('?' + parsed.query if scheme=='usb' else '')
    except ValueError:return ''


def device(uri,discovered):
    keys=[];label=''
    try:parsed=urlsplit(uri)
    except ValueError:return {'keys':[],'label':''}
    uuid=(parse_qs(parsed.query).get('uuid') or [''])[0].casefold().removeprefix('urn:uuid:')
    if re.fullmatch(r'[0-9a-f-]{36}',uuid):keys.append('uuid:'+uuid)
    direct=endpoint(uri)
    if direct:keys.append('endpoint:'+direct)
    if parsed.scheme=='dnssd':
        service=unquote(parsed.netloc).split('._')[0]
        if service:keys.append('service:'+service.casefold());label=service
    for row in discovered:
        observed_uuid=row.get('uuid','').casefold()
        observed_endpoint=endpoint(row.get('uri',''))
        if ('uuid:'+observed_uuid in keys or direct and direct==observed_endpoint or label and label.casefold()==row.get('label','').casefold()):
            if re.fullmatch(r'[0-9a-f-]{36}',observed_uuid):keys.append('uuid:'+observed_uuid)
            if observed_endpoint:keys.append('endpoint:'+observed_endpoint)
            label=row.get('label') or label
    return {'keys':sorted(set(keys)),'label':label}


def consolidate(rows):
    groups=[]
    for row in rows:
        keys=set(row.get('device',{}).get('keys',[]))
        if not keys:keys={'queue:'+row.get('node','local')+':'+row['name']}
        matches=[]
        for group in groups:
            a={key for key in group['keys'] if key.startswith('uuid:')};b={key for key in keys if key.startswith('uuid:')}
            if keys&group['keys'] and not (a and b and a!=b):matches.append(group)
        if len({key for group in matches for key in group['keys'] if key.startswith('uuid:')})>1:matches=[]
        if matches:
            group=matches[0];group['keys']|=keys;group['routes'].append(row)
            for other in matches[1:]:group['keys']|=other['keys'];group['routes']+=other['routes'];groups.remove(other)
        else:groups.append({'keys':keys,'routes':[row]})
    result=[]
    for group in groups:
        routes=sorted(group['routes'],key=lambda row:(row.get('node','local'),row['name']))
        keys=sorted(group['keys'],key=lambda key:(not key.startswith('uuid:'),key))
        labels=sorted({row.get('profile',{}).get('label') for row in routes if row.get('profile',{}).get('label')})
        discovered=sorted({row.get('device',{}).get('label') for row in routes if row.get('device',{}).get('label')})
        label=(labels or discovered or [routes[0]['name'].replace('_',' ')])[0]
        ident='printer-'+hashlib.sha256(keys[0].encode()).hexdigest()[:16]
        result.append({'id':ident,'name':label,'label':label,'aliases':labels,'identity_verified':not keys[0].startswith('queue:'),'routes':routes,'route_count':len(routes)})
    return sorted(result,key=lambda row:(row['label'].casefold(),row['id']))


def choose(value,query):
    rows=value.get('printers',[])
    def names(row):return [row['id'],row['label'],*row.get('aliases',[]),*[route['name'] for route in row['routes']]]
    exact=[row for row in rows if query.casefold() in [name.casefold() for name in names(row)]]
    matches=exact or [row for row in rows if all(term in row['label'].casefold() for term in query.casefold().split())]
    if len(matches)!=1:raise ValueError('Choose a printer from lk print'+(' — this name matches several printers' if matches else ' — destination not found'))
    return matches[0]


def route(destination,local_node=''):
    usable=[row for row in destination['routes'] if not re.search(r'\b(disabled|paused|unavailable)\b',row.get('status',''),re.I)]
    if not usable:raise ValueError('No enabled queue for this printer; inspect Routes or refresh')
    return sorted(usable,key=lambda row:(row.get('node') not in {'local',local_node},row.get('node',''),row['name']))[0]
