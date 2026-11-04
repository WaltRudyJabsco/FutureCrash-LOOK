"""Read-only Museum discovery for the shared assistant tool registry."""
import json
from urllib.parse import urlencode


def tools():
    return [{'type':'function','function':{'name':'museum_search','description':'Search downloaded Museum artwork by title, artist, period or subject on the configured Fabric collection owner. Returns actual metadata and image links; does not download, delete or start a slideshow. Use instead of guessing image folders.','parameters':{'type':'object','properties':{'query':{'type':'string','maxLength':500}},'additionalProperties':False}}}]


def run_tool(name,args):
    if name!='museum_search':raise ValueError('Unknown Museum tool')
    from museum_desk import Client,preference
    query=str(args.get('query') or '')
    if len(query)>500:raise ValueError('Museum query is too long')
    client=Client(preference());result=client.snapshot(query);items=[]
    for row in result.get('items',[])[:30]:
        item={key:row.get(key) for key in ('id','title','artist','date','medium','museum','rights','downloaded')}
        item['image_path']='/api/museum/image?'+urlencode({'target':client.node,'id':row['id']})
        items.append(item)
    return json.dumps({'ok':True,'owner':client.node,'items':items,'total':len(result.get('items',[])),'gallery_path':'/museum','offline':result.get('offline',False),'guidance':'Image links are relative to the Signal/Albert host; use lk museum for terminal viewing. Metadata is not visual analysis.'})
