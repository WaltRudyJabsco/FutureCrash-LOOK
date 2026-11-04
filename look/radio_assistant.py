"""YouTube Radio assistant tools use the same owner and queue as lk ytr."""
import json
import re
from urllib.parse import urlsplit


def intent(prompt):
    text=str(prompt or '')
    if not re.search(r'\b(?:ytr|youtube\s+radio)\b',text,re.I):return None
    if re.search(r"\b(?:don't|do not|never|without|how (?:do|can|would)|explain)\b",text,re.I):return None
    if re.match(r'\s*(?:how|why|what happened|when|explain|did|does|is|was|I (?:asked|said|tried))\b',text,re.I):return None
    if re.search(r'\b(?:add|queue|save|put)\b',text,re.I):
        urls=re.findall(r'https?://[^\s<>]+',text)
        if len(urls)!=1:return {'action':'add','error':'Paste exactly one YouTube link with your request to add it to YouTube Radio.'}
        url=urls[0].rstrip('.,!?)')
        parsed=urlsplit(url)
        if parsed.hostname not in {'youtube.com','www.youtube.com','m.youtube.com','music.youtube.com','youtu.be'} or parsed.username or parsed.password:return {'action':'add','error':'Use a YouTube video link for YouTube Radio.'}
        return {'action':'add','url':url}
    if re.search(r'\b(?:list|show|what|which)\b',text,re.I):return {'action':'list'}
    return None


def tools():
    return [dict(type='function',function=dict(name=name,description=description,parameters=dict(type='object',properties=props,required=required,additionalProperties=False))) for name,description,props,required in (
        ('radio_queue','List the shared YouTube Radio (YTR / lk ytr) queue and saved listening positions. This is not music library search.',{},[]),
        ('radio_add','Add a user-supplied YouTube link to the configured shared YouTube Radio listen-later queue. Does not start playback. Requires an explicit request to add/queue it.',{'url':{'type':'string'}},['url']))]


def run_tool(name,args,prompt=''):
    import ytr
    if name not in {'radio_queue','radio_add'}:raise ValueError('Unknown radio tool')
    if name=='radio_add':
        authority=intent(prompt)
        if not authority or authority.get('error') or authority.get('url')!=args.get('url'):raise ValueError('An explicit add-to-YTR request with this YouTube URL is required')
    client=ytr.Client(ytr.owner())
    result=client.request('add',url=args['url']) if name=='radio_add' else client.request()
    if name=='radio_add':
        receipt=result.get('radio_added',{})
        row=next((r for r in result.get('items',[]) if r.get('id')==receipt.get('id')),None)
        if not row:raise ValueError('The queue owner did not return a verified add receipt')
        return json.dumps(dict(ok=True,node=result.get('node',client.node),item=row,already_present=receipt.get('already_present',False),playback_started=False))
    return json.dumps(dict(ok=True,node=result.get('node',client.node),items=result.get('items',[]),offline=result.get('offline',False)))


def describe(result):
    if 'item' in result:
        return ('Already queued: ' if result['already_present'] else 'Added to YouTube Radio: ')+str(result['item'].get('title') or result['item'].get('id'))+' · owner '+str(result['node'])+'. Playback has not started.'
    return 'YouTube Radio · '+str(result['node'])+'\n'+('\n'.join('• '+str(r.get('title') or r.get('id'))+' · '+str(round(r.get('position',0)))+'s' for r in result['items'][:50]) or 'The queue is empty.')
