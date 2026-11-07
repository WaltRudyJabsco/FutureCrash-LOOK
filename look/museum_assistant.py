"""Read-only Museum discovery for the shared assistant tool registry."""
import json
import secrets
from urllib.parse import urlencode


def tools():
    return [{'type':'function','function':{'name':'museum_search','description':'Search Museum artwork by title, artist, period or subject on the configured Fabric collection owner. An artist surname alone is sufficient: use query Renoir for Renoir. For any/random artwork use an empty query and random=true; never search for the literal word random. Use returned IDs with print_artwork. Returns actual metadata and image links; does not download, delete or start a slideshow. Use instead of guessing image folders.','parameters':{'type':'object','properties':{'query':{'type':'string','maxLength':500},'random':{'type':'boolean'},'downloaded_only':{'type':'boolean'}},'additionalProperties':False}}}]


def run_tool(name,args):
    if name!='museum_search':raise ValueError('Unknown Museum tool')
    from museum_desk import Client,preference
    query=str(args.get('query') or '')
    if len(query)>500:raise ValueError('Museum query is too long')
    if query.strip().casefold() in {'random','random image','random artwork'}:query=''
    client=Client(preference());result=client.snapshot(query);items=[]
    rows=result.get('items',[])
    if args.get('downloaded_only'):rows=[r for r in rows if r.get('downloaded') or r.get('available_offline')]
    if args.get('random'):
        rows=[r for r in rows if (r.get('downloaded') or r.get('available_offline')) and not r.get('removal_due')]
        rows=secrets.SystemRandom().sample(rows,min(5,len(rows)))
    for row in rows[:30]:
        item={key:row.get(key) for key in ('id','title','artist','date','medium','museum','rights','downloaded')}
        item['image_path']='/api/museum/image?'+urlencode({'target':client.node,'id':row['id']})
        items.append(item)
    return json.dumps({'ok':True,'owner':client.node,'items':items,'total':len(result.get('items',[])),'gallery_path':'/museum','offline':result.get('offline',False),'guidance':'Image links are relative to the Signal/Albert host; use lk museum for terminal viewing. Metadata is not visual analysis.'})
