"""Fabric printing CLI and bounded assistant hooks. Explicit text-print requests can submit one bounded job."""
import subprocess
import argparse
import base64
import json
import re
from pathlib import Path
import sys
import fabric_files
from print_core import MAX_INPUT_BYTES


def _request(action='list',node='local',**fields):
    if action=='list' and node=='all':return fabric_files.request('/v1/print/fabric',timeout=60)
    return fabric_files.request('/v1/print',{'target':node},json.dumps(dict(action=action,**fields)).encode(),timeout=60)


def destinations():
    value=_request('list','all')
    if value.get('printers') and 'routes' not in value['printers'][0]:
        from print_destinations import consolidate
        value=dict(value,queues=value['printers'],printers=consolidate(value['printers']))
    return value


def request(action='list',node='local',**fields):
    if action=='list' and node=='all':return destinations()
    if node!='auto':return _request(action,node,**fields)
    from print_destinations import choose,route
    value=destinations();destination=choose(value,fields['queue'])
    if action in {'jobs','nickname'}:
        results=[]
        for candidate in destination['routes']:
            try:results.append(_request(action,candidate['node'],**dict(fields,queue=candidate['name'])))
            except (OSError,RuntimeError,ValueError) as error:results.append({'node':candidate['node'],'queue':candidate['name'],'error':str(error)})
        return {'printer':destination['label'],'view':action,'routes':results}
    selected=route(destination,value.get('local_node',''))
    # Choose before dispatch. Never fail over a write after it may have arrived.
    result=_request(action,selected['node'],**dict(fields,queue=selected['name']))
    return dict(result,destination=destination['label'])


def prepare(queue,node='auto',path=None,text=None,receipt=False,**options):
    if (path is None)==(text is None):raise ValueError('Choose exactly one file or text')
    if path is not None:
        source=Path(path).expanduser().resolve()
        if not source.is_file() or source.stat().st_size>MAX_INPUT_BYTES:raise ValueError('Choose a file up to 3 MiB')
        with source.open('rb') as stream:data=stream.read(MAX_INPUT_BYTES+1)
        title=source.name
        kind=('receipt-text' if source.suffix.casefold() in {'.txt','.md','.markdown'} else 'receipt-image') if receipt else 'document'
    else:
        data=str(text).encode('utf-8');title='LOOK receipt.txt' if receipt else 'LOOK text.txt'
        kind='receipt-text' if receipt else 'document'
    if not 0<len(data)<=MAX_INPUT_BYTES:raise ValueError('Print input must be 1 byte–3 MiB')
    result=request('prepare',node,queue=queue,data=base64.b64encode(data).decode(),filename=title,kind=kind,options_value=options)
    result['send_command']='lk print send '+result['id']+' --node '+result.get('node',node)+' --confirm'
    return result


MAX_QUICK_TEXT = 8000


def prepare_short_text(queue, text, exact_label=False):
    """Resolve once and pin the owner before preparing and submitting one copy."""
    from print_destinations import choose, route
    if not isinstance(text,str) or not text.strip() or len(text)>MAX_QUICK_TEXT:
        raise ValueError('Quick printing accepts 1–8,000 characters; use a reviewed plan for longer documents')
    catalog=destinations();destination=choose(catalog,queue)
    if exact_label and destination['label'].casefold()!=queue.casefold():
        raise ValueError('Use the exact friendly printer name from discovery')
    selected=route(destination,catalog.get('local_node',''))
    plan=prepare(selected['name'],selected['node'],text=text,
                 receipt=selected.get('profile',{}).get('kind')=='escpos',copies=1)
    return dict(plan,destination=destination['label'])


def quick_text(queue,text,exact_label=False):
    plan=prepare_short_text(queue,text,exact_label)
    return dict(request('send',plan['node'],ident=plan['id'],confirm=True),destination=plan['destination'])


def clipboard_print(ui,queue=None):
    from look_renderer import prompt_line
    from print_desk import pick
    import clipboard_shelf
    import clipboard_items
    import tempfile
    def printable(value):
        try:
            item=clipboard_items.unpack(value)
            return bool(value) and (not item or Path(item['name']).suffix.lower() in {'.pdf','.txt','.md','.markdown','.png','.jpg','.jpeg'})
        except (ValueError,TypeError):return False
    reason='Current clipboard is empty or not a printable type.'
    try:content=clipboard_shelf.read_item(for_print=True)
    except (OSError,ValueError,subprocess.SubprocessError) as exc:
        content=None;reason='Current clipboard unavailable: '+str(exc)
    while not printable(content):
        print('Choose a printable clipboard item: text, image, or PDF.')
        content=clipboard_shelf.show(pick=True,initial_notice=reason)
        if content is None:return 'Cancelled.'
    item=clipboard_items.unpack(content)
    if item:
        with tempfile.TemporaryDirectory(prefix='look-clip-print-') as folder:
            source=Path(folder)/item['name'];source.write_bytes(item['data'])
            result=selected_file(source,ui,prefer_receipt=source.suffix.lower()!='.pdf',queue=queue)
        return 'Print review closed.' if result==0 else 'Print was not completed; see the error above.'
    content=content.replace('\r\n','\n').replace('\r','\n').strip()
    if len(content)>MAX_QUICK_TEXT:raise ValueError('Copy a shorter selection (up to 8,000 characters).')
    if any(not ch.isprintable() and ch not in '\t\n' for ch in content):
        raise ValueError('Copy plain text without control characters.')
    if not queue:
        choice=pick(ui,prefer_receipt=True)
        if not choice:return 'Cancelled.'
        queue=choice['id']
    plan=prepare_short_text(queue,content)
    print(content)
    print('One copy on '+plan['destination'])
    if 'estimated_paper_mm' in plan:print(f"Estimated paper: {plan['estimated_paper_mm']/10:.1f} cm")
    try:answer,cancel=prompt_line('Print this text? [y yes · Enter/Esc cancel] ')
    except (KeyboardInterrupt,EOFError):answer,cancel='',True
    if cancel or answer.strip().casefold() not in {'y','yes'}:
        request('discard',plan['node'],ident=plan['id'],confirm=True)
        return 'Cancelled.'
    result=request('send',plan['node'],ident=plan['id'],confirm=True)
    return design_summary(dict(result,destination=plan['destination']))


def explicit_print(prompt, label):
    text=' '.join(str(prompt or '').casefold().replace('’',"'").split())
    label=' '.join(label.casefold().split())
    if not label or not re.search(r'(?<!\w)'+re.escape(label)+r'(?!\w)',text):return False
    if re.match(r'^(?:what|why|when|where|did|does|is|was|i (?:said|asked|tried)|(?:can|could|would|should) (?!you\b))\b',text):return False
    if re.search(r"\b(?:don't|do not|never|without|not yet|preview|draft|explain|how|can i|could i|should i)\b",text):return False
    return bool(re.search(r'\bprint\b',text) or re.search(r'\bsend\b.*\bto (?:the )?'+re.escape(label)+r'(?!\w)',text))


def preferred_receipt(prompt=""):
    """A preference belongs to the physical destination, visible to every peer."""
    catalog=destinations()
    if any(re.search(r'(?<!\w)'+re.escape(p['label'])+r'(?!\w)',prompt,re.I) for p in catalog.get('printers',[])):
        raise ValueError('A printer was named: pass its exact label as queue instead of using the default')
    matches=[p for p in catalog.get('printers',[]) if any(
        r.get('profile',{}).get('preferred_receipt') is True
        and r.get('profile',{}).get('kind')=='escpos' for r in p.get('routes',[]))]
    if len(matches)!=1:
        labels=[p['label'] for p in catalog.get('printers',[])]
        raise ValueError('Choose a printer; no unique preferred receipt destination. '+
                         '; '.join(f'{i}. {label}' for i,label in enumerate(labels,1)))
    return matches[0]['label']


def explicit_default_print(prompt):
    # Reuse the named-print guard, but never silently override an explicit destination.
    if re.search(r'\b(?:on|to|using)\s+(?:the\s+)?[^.!?]*\bprinter\b',str(prompt),re.I):return False
    return explicit_print(str(prompt)+' on configured receipt destination','configured receipt destination')


def printable_file(path):
    source=Path(path).expanduser().resolve()
    if not source.is_file():raise ValueError('Choose one regular file to print; folders are not printable')
    if source.suffix.casefold() not in {'.pdf','.txt','.md','.markdown','.png','.jpg','.jpeg'}:raise ValueError('Print PDF, UTF-8 text, PNG or JPEG; export other documents/manuscripts to PDF first')
    if not 0<source.stat().st_size<=MAX_INPUT_BYTES:raise ValueError('Choose a nonempty file up to 3 MiB')
    return source


def prepare_file(queue,path,node='auto',receipt=None,**options):
    """All frontends share the same file validation and pinned destination route."""
    source=printable_file(path)
    if node=='auto':
        from print_destinations import choose,route
        value=destinations();destination=choose(value,queue)
        selected=route(destination,value.get('local_node',''));label=destination['label'];owner=selected['node']
    else:
        value=request('list',node)
        rows=[row for row in value.get('printers',[]) if row['name']==queue or row.get('profile',{}).get('label','').casefold()==queue.casefold()]
        if len(rows)!=1:raise ValueError('Choose an exact queue on this owner')
        selected=rows[0];owner=value.get('node',node);label=selected.get('profile',{}).get('label',selected['name'])
    is_receipt=selected.get('profile',{}).get('kind')=='escpos'
    if receipt is not None and receipt!=is_receipt:raise ValueError('Requested print format does not match the selected printer profile')
    if is_receipt and source.suffix.casefold()=='.pdf':raise ValueError('Choose a document printer for PDF; receipt printers accept text or raster images')
    result=prepare(selected['name'],owner,path=source,receipt=is_receipt,**options)
    return dict(result,destination=label)


def artwork_caption(row):
    return [' '.join(str(row.get(key) or '').split())[:250] for key in ('title','artist','date','museum')]

def selected_file(path,ui,prefer_receipt=False,default_style="image",caption=None,queue=None):
    """Foreground file-manager handoff: choose, review, explicitly print, return."""
    from print_desk import pick
    from look_renderer import prompt_line
    plan=None
    try:
        source=printable_file(path)
        choice={'id':queue} if queue else (pick(ui,prefer_receipt=True) if prefer_receipt else pick(ui))
        if not choice:return 0
        options={'caption':caption} if caption else {}
        if source.suffix.casefold()=='.pdf':
            value,cancelled=prompt_line('PDF pages to print (required, e.g. 1 or 1-3): ')
            if cancelled or not value.strip():return 0
            options['pages']=value.strip()
        if source.suffix.casefold() in {'.png','.jpg','.jpeg'}:
            import clipboard_image
            preview=clipboard_image.process(source)
            print(f"Image preview · {source.name} · {preview['size'][0]} × {preview['size'][1]} pixels")
            print(preview['preview'])
        elif source.suffix.casefold() in {'.txt','.md','.markdown'}:
            print(source.read_text(encoding='utf-8')[:8000])
        value,cancelled=prompt_line('Copies [1]: ')
        if cancelled:return 0
        options['copies']=int(value.strip() or '1')
        if source.suffix.casefold() in {'.png','.jpg','.jpeg'}:
            value,cancelled=prompt_line('Print style image/ascii ['+default_style+']: ')
            if cancelled:return 0
            options['style']=value.strip().lower() or default_style
            value,cancelled=prompt_line('Rotate clockwise 0/90 [0]: ')
            if cancelled:return 0
            options['rotation']=int(value.strip() or '0')
        value,cancelled=prompt_line('Paper allowance: receipt 1 ft / banner 10 ft [receipt]: ')
        if cancelled:return 0
        mode=value.strip().lower() or 'receipt'
        if mode not in {'receipt','banner'}:raise ValueError('Choose receipt or banner')
        if mode=='banner':options['paper_limit_mm']=3048
        plan=prepare_file(choice['id'],source,**options)
        display(plan)
        answer,cancelled=prompt_line('Print '+source.name+' on '+plan['destination']+' via '+plan['node']+'? [p prints · Enter/Esc cancels] ')
        if cancelled or answer.strip().casefold()!='p':
            request('discard',plan['node'],ident=plan['id'],confirm=True)
            print('Print cancelled; the prepared content was discarded.')
            return 0
        result=request('send',plan['node'],ident=plan['id'],confirm=True)
        display(result)
        prompt_line('Enter returns to LOOK. ')
        return 0 if result.get('state') in {'queued','submitting','printing'} else 1
    except KeyboardInterrupt:
        if plan:
            # Only discard an unsent draft. Never attempt a second submission.
            try:request('discard',plan['node'],ident=plan['id'],confirm=True)
            except (OSError,RuntimeError,ValueError):pass
        return 0
    except (OSError,ValueError,RuntimeError) as error:
        print('LOOK Print: '+str(error))
        if plan:print('Inspect this plan before retrying: '+plan['id']+' on '+plan['node'])
        prompt_line('Enter returns to LOOK. ')
        return 1


def parser():
    result=argparse.ArgumentParser(prog='lk print',description='Fabric printers and reviewed print plans; nothing prints during discovery/preparation.')
    result.add_argument('--json',action='store_true',help='Machine-readable result')
    sub=result.add_subparsers(dest='action')
    sub.add_parser('setup',help='Install offline pyfiglet and image rendering for this account')
    for kind in ('banner','fortune','fortune-cookie'):
        item=sub.add_parser(kind);item.add_argument('text',nargs='?' if kind=='fortune-cookie' else None);item.add_argument('--font',default='solid',choices=['solid','standard','small','slant','banner','big']);item.add_argument('--printer');item.add_argument('--paper-limit-mm',type=float,default=304.8)
    item=sub.add_parser('completion');item.add_argument('--confirm',action='store_true');item.add_argument('--node',default='local')
    for action in ['list','discover']:
        item=sub.add_parser(action);item.add_argument('--node',default='all' if action=='list' else 'local')
        if action=='list':item.add_argument('--queues',action='store_true',help='Show underlying owner/queue routes')
    for action in ['options','jobs']:
        item=sub.add_parser(action);item.add_argument('queue',nargs='?');item.add_argument('--node',default='auto')
    item=sub.add_parser('add');item.add_argument('queue');item.add_argument('--uri',required=True);item.add_argument('--driver',choices=['everywhere','raw'],default='everywhere');item.add_argument('--confirm',action='store_true');item.add_argument('--node',default='local')
    item=sub.add_parser('nickname');item.add_argument('queue',nargs='?');item.add_argument('label',nargs='?');item.add_argument('--confirm',action='store_true');item.add_argument('--node',default='auto')
    item=sub.add_parser('bluetooth',help='Register an observed MXW01 Bluetooth receipt printer on its owner');item.add_argument('queue');item.add_argument('--address',required=True);item.add_argument('--adapter',required=True);item.add_argument('--label',default='Tiny Printer');item.add_argument('--confirm',action='store_true');item.add_argument('--node',default='local')
    item=sub.add_parser('profile');item.add_argument('queue');item.add_argument('--kind',choices=['document','escpos'],required=True);item.add_argument('--width',type=int,default=384);item.add_argument('--columns',type=int,default=32);item.add_argument('--image-mode',choices=['raster','column24'],default='raster');item.add_argument('--max-receipt-bytes',type=int,default=None,help='Device-specific encoded receipt limit; 0 disables');item.add_argument('--preferred-receipt',action=argparse.BooleanOptionalAction,default=None,help='Use this receipt destination when an assistant print request omits the printer');item.add_argument('--confirm',action='store_true');item.add_argument('--node',default='local')
    for action in ['file','text','receipt']:
        item=sub.add_parser(action);item.add_argument('content',nargs='?' if action=='receipt' else None);item.add_argument('--image');item.add_argument('--printer');item.add_argument('--node',default='auto');item.add_argument('--paper-limit-mm',type=float);item.add_argument('--copies',type=int,default=1);item.add_argument('--style',choices=['image','ascii']);item.add_argument('--rotation',type=int,choices=[0,90]);item.add_argument('--pages');item.add_argument('--media');item.add_argument('--sides',choices=['one-sided','two-sided-long-edge','two-sided-short-edge'])
    item=sub.add_parser('clip',aliases=['clipboard'],help='Review copied text, images or files; choose from history when unavailable');item.add_argument('--printer')
    item=sub.add_parser('quick',help='Send one text receipt/document immediately to a named printer')
    item.add_argument('content');item.add_argument('--printer',required=True)
    for action in ['inspect','send','discard']:
        item=sub.add_parser(action);item.add_argument('ident');item.add_argument('--node',default='local')
        if action!='inspect':item.add_argument('--confirm',action='store_true')
    item=sub.add_parser('cancel');item.add_argument('queue');item.add_argument('job');item.add_argument('--confirm',action='store_true');item.add_argument('--node',default='local')
    for child in dict.fromkeys(sub.choices.values()):child.add_argument('--json',action='store_true',default=argparse.SUPPRESS)
    return result


def destination_label(row):
    label=row.get('profile',{}).get('label')
    return row['label'] if 'routes' in row else label+' ['+row['name']+']' if label and label!=row['name'] else row['name']


def display(result):
    if isinstance(result.get('options'),str) or isinstance(result.get('jobs'),str) or result.get('view')=='jobs':
        import print_details,shutil,terminal_style
        view='options' if 'options' in result else 'jobs'
        if 'jobs' in result:result={'routes':[result]}
        colors=terminal_style.list_colors() if sys.stdout.isatty() else None
        print('\n'.join(print_details.render(view,result,shutil.get_terminal_size((80,24)).columns,colors)))
        return
    if 'printers' in result:
        print('FABRIC PRINTERS')
        for row in result['printers']:print('  '+destination_label(row)+(' · '+str(row['route_count'])+' routes' if 'routes' in row else ' @ '+row.get('node','local')+' · '+row.get('profile',{}).get('kind','document')+' · '+row.get('status','')))
        if not result['printers']:print('No configured queues visible. Run lk print discover --node OWNER or open that computer’s printer settings.')
        for error in result.get('errors',[]):print('Unavailable: '+str(error.get('node','owner'))+' · '+str(error.get('error','')))
    elif 'id' in result and 'state' in result:
        print('PRINT PLAN · '+result['state']+' · '+result.get('title',''))
        print('Printer: '+result['queue']+' @ '+result.get('node','local')+' · '+result['kind']+' · '+str(result['bytes'])+' bytes')
        if 'estimated_paper_mm' in result:print(f"Paper: about {result['estimated_paper_mm']/10:.1f} cm · limit {result['max_paper_mm']/10:g} cm")
        print('Options: '+', '.join(k+'='+str(v) for k,v in result['options'].items()))
        print(result['note'])
        if result.get('text_preview'):print('Text preview'+(' (truncated)' if result.get('preview_truncated') else '')+':\n'+result['text_preview'])
        if result.get('receipt'):print(json.dumps(result['receipt'],ensure_ascii=False))
        print(result.get('send_command','Plan: '+result['id']))
    else:
        for key,value in result.items():
            if key not in {'ok','node'}:print(key+': '+(json.dumps(value,ensure_ascii=False) if isinstance(value,(dict,list)) else str(value)))


def main(args,ui=None):
    if not args and sys.stdin.isatty() and sys.stdout.isatty():
        from print_desk import desk
        return desk(ui)
    selected=parser().parse_args(args or ['list']);value=vars(selected);action=value.pop('action');node=value.pop('node','all');as_json=value.pop('json',False)
    try:
        if action in ('clip','clipboard'):
            if as_json or not sys.stdin.isatty() or not sys.stdout.isatty():raise ValueError('Open lk print clip in a terminal to review the selection.')
            print(clipboard_print(ui,value['printer']));return 0
        if action=='setup':
            import print_design
            print(print_design.setup());return 0
        if action=='banner' and not as_json and sys.stdin.isatty() and sys.stdout.isatty():
            from look_renderer import prompt_line
            from print_desk import pick
            import print_design
            print(print_design.banner_preview(value['text'],value['font']))
            queue=value['printer']
            if not queue:
                answer,cancel=prompt_line('Choose a printer? [p choose · Enter/Esc done] ')
                if cancel or answer.strip().casefold()!='p':return 0
                choice=pick(ui,prefer_receipt=True)
                if not choice:return 0
                queue=choice['id']
            plan=design(value['text'],kind='banner',font=value['font'],queue=queue,paper_limit_mm=value['paper_limit_mm'])
            print('Banner on '+plan['destination'])
            if 'estimated_paper_mm' in plan:print(f"Estimated paper: {plan['estimated_paper_mm']/10:.1f} cm")
            try:
                answer,cancel=prompt_line('Print one banner? [y yes · Enter/Esc cancel] ')
            except (EOFError,KeyboardInterrupt):
                answer,cancel='',True
            if cancel or answer.strip().casefold() not in {'y','yes'}:
                request('discard',plan['node'],ident=plan['id'],confirm=True)
                print('Banner cancelled.')
                return 0
            result=request('send',plan['node'],ident=plan['id'],confirm=True)
            print(design_summary(dict(result,destination=plan['destination'],design=plan['design'])))
            return 0 if result.get('state') in {'queued','submitting','printing'} else 1
        if action in {'banner','fortune','fortune-cookie'}:
            result=design(value['text'],kind=action,font=value['font'],queue=value['printer'],paper_limit_mm=value['paper_limit_mm'])
            if 'ascii_preview' in result and not as_json:
                print(result['ascii_preview'])
                print('Preview only. Add --printer "PRINTER NAME" to review a print job, then run the send command shown.',file=sys.stderr)
            elif as_json:print(json.dumps(result))
            else:display(result)
            return 0
        if action in {'options','jobs','nickname'} and not value.get('queue') or action in {'file','text','receipt'} and not value.get('printer'):
            if not sys.stdin.isatty() or not sys.stdout.isatty():raise ValueError('Choose a printer; run lk print in a terminal or pass --printer/queue')
            from print_desk import pick
            choice=pick(ui,node=node)
            if not choice:return 0
            value['printer' if action in {'file','text','receipt'} else 'queue']=choice['id'] if node=='auto' else choice['routes'][0]['name']
        if action=='nickname' and not value.get('label'):
            if not sys.stdin.isatty() or not sys.stdout.isatty():raise ValueError('Provide a nickname, or use lk print in a terminal')
            from look_renderer import prompt_line
            value['label'],cancelled=prompt_line('Printer nickname: ')
            if cancelled:return 0
        queues=value.pop('queues',False)
        if action in {'file','text','receipt'}:
            content=value.pop('content');image=value.pop('image');queue=value.pop('printer')
            if image and (action!='receipt' or content):raise ValueError('--image is only for receipt images, without text')
            if action=='receipt' and not content and not image:raise ValueError('Choose receipt text or --image FILE')
            if content=='-' and action!='file':content=sys.stdin.buffer.read(MAX_INPUT_BYTES+1).decode('utf-8')
            options={k:v for k,v in value.items() if v is not None}
            result=prepare_file(queue,content,node,**options) if action=='file' else prepare(queue,node,path=image,text=None if image else content,receipt=action=='receipt',**options)
        elif action=='quick':
            content=value['content']
            if content=='-':content=sys.stdin.read(MAX_QUICK_TEXT+1)
            result=quick_text(value['printer'],content)
        else:result=request(action or 'list',node,**value)
        if queues:result=dict(result,printers=result.get('queues',[]))
        if as_json:print(json.dumps(result,ensure_ascii=False,indent=2))
        else:display(result)
        return 0
    except (OSError,ValueError,RuntimeError) as error:print('LOOK Print: '+str(error));return 1


def design(text=None,kind='banner',font='solid',queue=None,paper_limit_mm=304.8):
    import print_design
    if queue is None:
        if kind=='fortune-cookie' and text is None:
            import fortune_deck,secrets
            text=secrets.choice(fortune_deck.LINES)
        if kind=='banner':return {'kind':kind,'font':font,'ascii_preview':print_design.banner_preview(text,font),'fonts':('solid',*print_design.FONTS)}
        _,details=print_design.render(text,kind,font,artwork=print_design.museum_artwork() if kind=='fortune' else None);return details
    from print_destinations import choose,route
    catalog=destinations();destination=choose(catalog,queue);selected=route(destination,catalog.get('local_node',''))
    profile=selected.get('profile',{});receipt=profile.get('kind')=='escpos'
    if kind=='fortune-cookie' and text is None:
        text=_request('draw-cookie',selected['node'],queue=selected['name'])['text']
    if kind in ('fortune','fortune-cookie'):paper_limit_mm=304.8
    image,details=print_design.render(text,kind,font,profile.get('width',384) if receipt else 576,artwork=print_design.museum_artwork() if kind=='fortune' else None)
    result=_request('prepare',selected['node'],queue=selected['name'],data=base64.b64encode(image).decode(),filename=kind+'.png',kind='receipt-image' if receipt else 'document',options_value={'copies':1,'paper_limit_mm':paper_limit_mm})
    result.update(destination=destination['label'],design=details)
    result['send_command']='lk print send '+result['id']+' --node '+result['node']+' --confirm'
    return result


def design_summary(result):
    state=result.get('state','unknown');label=result.get('destination',result.get('queue','printer'))
    receipt=result.get('receipt') or {};ident=result.get('id','')
    subject={'fortune':'Fortune','fortune-cookie':'Fortune cookie','banner':'Banner'}.get(result.get('design',{}).get('kind'),'Print job')
    if state in {'submitting','printing'}:return subject+' accepted by '+label+'; delivery is not yet confirmed. Check lk print inspect '+ident+' --node '+str(result.get('node','local'))+'.'
    if state=='queued':return subject+' sent to '+label+'. '+receipt.get('note','Check the physical output.')+' Job '+ident+'.'
    if state=='prepared':return subject+' prepared, not printed. '+result.get('send_command','Review job '+ident+'.')
    return subject+' status: '+state+'. '+receipt.get('error',receipt.get('note','Check printer jobs; do not resend automatically.'))+' Job '+ident+'.'


def tools():
    fields={'node':{'type':'string','description':'Optional exact owner; default auto selects an enabled route'},'queue':{'type':'string','description':'Stable physical printer ID or unique friendly name from discovery; an exact queue works with an explicit owner'}}
    return [
        {'type':'function','function':{'name':'banner_render','description':'Render offline FIGlet lettering for a banner preview. No printing. Fonts: standard, small, slant, banner, big.','parameters':{'type':'object','properties':{'text':{'type':'string','maxLength':120},'font':{'type':'string','enum':['standard','small','slant','banner','big']}},'required':['text'],'additionalProperties':False}}},
        {'type':'function','function':{'name':'print_design','description':'Prepare or explicitly print a banner or fortune-cookie slip. For fortunes write an original, thoughtful/playful fortune of one to three short lines (prefer under 90 characters); omit text for a standard fortune-cookie to draw from the owner’s 200-line deck; provide text for custom wording. Both include lucky numbers. Choose fortune-cookie for a short text slip or fortune for the illustrated card with a saved Museum artwork and credit; no new outside downloads. Landscape artwork rotates independently of the upright fortune text. Banners default to solid sideways letters. Choose a FIGlet font for ASCII lettering. Discover the exact friendly printer label first. send defaults false; set true only for an explicit current request to print to that named printer. One attempt per turn. Longer banners require an explicitly requested banner allowance. Never claim physical appearance from a receipt.','parameters':{'type':'object','properties':{'text':{'type':'string','maxLength':140},'kind':{'type':'string','enum':['banner','fortune','fortune-cookie']},'font':{'type':'string','enum':['solid','standard','small','slant','banner','big']},'queue':{'type':'string'},'paper_limit_mm':{'type':'number','minimum':1,'maximum':3048},'send':{'type':'boolean'}},'required':['kind','queue'],'additionalProperties':False}}},
        {'type':'function','function':{'name':'print_text','description':'Compose and print a short Markdown document when the user explicitly requests paper output. First retrieve needed facts with weather, web or Notes tools; do not invent forecasts. Use headings, short paragraphs and lists; include location, dates, units and source for forecasts. Omit queue to use the configured preferred receipt printer, or use the exact printer named by the user. No default means ask the user to choose. One copy, at most 8000 characters, normal paper limit, no automatic retries. Report queue acceptance rather than physical delivery. Use print_prepare for previews.','parameters':{'type':'object','properties':{'queue':{'type':'string','description':'Named destination; omit to use the user-configured receipt default'},'text':{'type':'string','maxLength':8000}},'required':['text'],'additionalProperties':False}}},
        {'type':'function','function':{'name':'printers_list','description':'List physical printers once across the trusted Fabric, with stable ID, friendly name and underlying queue routes. No setup or printing.','parameters':{'type':'object','properties':{},'additionalProperties':False}}},
        {'type':'function','function':{'name':'printer_inspect','description':'Inspect printer options or jobs on an exact owner/queue.','parameters':{'type':'object','properties':dict(fields,view={'type':'string','enum':['options','jobs']}),'required':['queue'],'additionalProperties':False}}},
        {'type':'function','function':{'name':'print_prepare','description':'Prepare a text/document/receipt job for user review, NEVER send paper. Return immutable plan, options and confirmation command. Choose a physical printer from discovery; automatic routing hides its underlying queues. Export DOCX/manuscripts to PDF before preparing.','parameters':{'type':'object','properties':dict(fields,path={'type':'string'},text={'type':'string'},receipt={'type':'boolean','description':'True for a configured ESC/POS receipt destination; false for document printers'},copies={'type':'integer','minimum':1,'maximum':20},style={'type':'string','enum':['image','ascii']},rotation={'type':'integer','enum':[0,90]},paper_limit_mm={'type':'number','minimum':1,'maximum':3048,'description':'Explicit paper allowance in mm; default 304.8 (one foot). Larger values are deliberate banner jobs.'},pages={'type':'string'},media={'type':'string'},sides={'type':'string','enum':['one-sided','two-sided-long-edge','two-sided-short-edge']}),'required':['queue'],'additionalProperties':False}}}]


def run_tool(tool,args,workspace,prompt='',turn=None):
    value=dict(args)
    if tool=='banner_render':
        if set(value)-{'text','font'}:raise ValueError('Only text and font are supported')
        return json.dumps(design(**{'font':'standard',**value}))
    if tool=='print_design':
        if set(value)-{'text','kind','font','queue','paper_limit_mm','send'}:raise ValueError('Unsupported design option')
        send=value.pop('send',False)
        if type(send) is not bool:raise ValueError('send must be boolean')
        if send:
            if not isinstance(value.get('queue'),str) or not explicit_print(prompt,value['queue']):raise ValueError('Ask explicitly to print to a named printer')
            if turn is None or turn.get('print_attempted'):raise ValueError('Only one print attempt per user message')
            if value.get('paper_limit_mm',304.8)>304.8 and not re.search(r'\b(banner|feet|foot|ticker)\b',prompt,re.I):raise ValueError('Ask explicitly for a longer banner allowance')
            turn['print_attempted']=True
        result=design(**value)
        if send:
            if result['destination'].casefold()!=value['queue'].casefold():
                request('discard',result['node'],ident=result['id'],confirm=True)
                raise ValueError('Use the exact friendly printer name')
            if turn.get('progress'):turn['progress']('Sending to '+result['destination']+'…')
            result=dict(request('send',result['node'],ident=result['id'],confirm=True),destination=result['destination'],design=result['design'])
        return json.dumps(result)
    if tool=='print_text':
        if set(value)-{'queue','text'} or 'text' not in value:
            raise ValueError('Use text and an optional printer queue')
        queue=value.get('queue')
        if not queue:
            if not explicit_default_print(prompt):raise ValueError('Ask explicitly to print; name any requested destination')
            queue=preferred_receipt(prompt)
        elif not isinstance(queue,str) or not explicit_print(prompt,queue):
            raise ValueError('Ask explicitly to print to a named printer; previews and questions do not send paper')
        if re.search(r'\b(weather|forecast)\b',prompt,re.I) and not (turn or {}).get('weather_verified'):
            raise ValueError('Fetch live weather successfully before composing and printing the forecast')
        if turn is None or turn.get('print_attempted'):
            raise ValueError('Only one quick print attempt per user message; inspect jobs before requesting another')
        turn['print_attempted']=True
        return json.dumps(quick_text(queue,value['text'],exact_label=True))
    if tool=='printers_list':return json.dumps(request('list','all'))
    if tool=='printer_inspect':
        if set(value)-{'view','node','queue'}:raise ValueError('Printer inspection accepts only owner, queue and options/jobs view')
        view=value.pop('view','options')
        if view not in {'options','jobs'}:raise ValueError('Printer inspection is read-only: choose options or jobs')
        return json.dumps(request(view,value.pop('node','auto'),**value))
    if tool!='print_prepare':raise ValueError('Unknown print tool')
    if value.get('path'):
        path=Path(value['path']).expanduser()
        path=(Path(workspace)/path).resolve() if not path.is_absolute() else path.resolve()
        if not path.is_relative_to(Path(workspace).resolve()):raise ValueError('Print files must be inside the current workspace; explicitly copy/export the document there first')
        value['path']=str(path)
        return json.dumps(prepare_file(**value))
    return json.dumps(prepare(**value))


def song_receipt(ui,entry,cover_path):
    from print_desk import pick
    from print_destinations import route
    from print_design import song_bitmap
    from look_renderer import prompt_line
    import io
    choice=pick(ui,prefer_receipt=True)
    if not choice:return 'Cancelled.'
    selected=route(choice,destinations().get('local_node',''))
    profile=selected.get('profile',{})
    receipt=profile.get('kind')=='escpos'
    width=profile.get('width',384) if receipt else 576
    cover=cover_path(entry)
    card=song_bitmap(entry,cover,width)
    out=io.BytesIO()
    card.save(out,format='PNG')
    plan=_request('prepare',selected['node'],queue=selected['name'],data=base64.b64encode(out.getvalue()).decode(),filename='Now playing.png',kind='receipt-image' if receipt else 'document',options_value={'copies':1})
    print('Track receipt · '+entry['title']+' · '+choice['label'])
    if not cover:print('Text only · album cover unavailable')
    if 'estimated_paper_mm' in plan:print(f"Estimated paper: {plan['estimated_paper_mm']/10:.1f} cm")
    try:answer,cancel=prompt_line('Print one track receipt? [y yes · Enter/Esc cancel] ')
    except (KeyboardInterrupt,EOFError):answer,cancel='',True
    if cancel or answer.strip().casefold() not in {'y','yes'}:
        request('discard',selected['node'],ident=plan['id'],confirm=True)
        return 'Cancelled.'
    result=request('send',selected['node'],ident=plan['id'],confirm=True)
    if profile.get('transport')=='mxw01-ble':
        receipt=result.get('receipt') or {}
        if receipt.get('completion_acknowledged'):
            return choice['label']+' confirmed completion.'
        if result.get('state')=='failed' and 'connection failed' in receipt.get('error','').lower():
            return 'Nothing sent. Wake '+choice['label']+' and press P to try again.'
        if result.get('state') in {'printing','submitting'}:
            return 'Delivery pending. Check lk print jobs "'+choice['label']+'".'
    return design_summary(dict(result,destination=choice['label']))
