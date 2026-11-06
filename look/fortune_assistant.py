"""Narrow fortune-print requests: discover, generate, submit once, report receipt."""
import json
from pathlib import Path
import re
import sys
import time


def intent(prompt):
    text=' '.join(str(prompt or '').strip().split())
    text=re.sub(r'^/fortune(?=\s|$)','print a fortune',text,flags=re.I)
    text=re.sub(r'\bforutne\b','fortune',text,flags=re.I)
    bare=re.fullmatch(r'(?:a )?(fortune(?: cookie)?)(?:,? please)?[.!?]?',text,re.I)
    if bare:return {'printer':'','kind':bare[1].lower().replace(' ','-')}
    match=re.fullmatch(r'(?:please\s+|(?:can|could|would) you\s+)?print\s+(?:me\s+)?(?:a\s+)?(fortune(?: cookie)?)(?:\s+(?:on|to|with)\s+(?:the\s+)?(.+?))?[.!?]?',text,re.I)
    return {'printer':(match.group(2) or '').rstrip('.!?'),'kind':match[1].lower().replace(' ','-')} if match else None


def printer_menu(name,labels):
    return 'Choose a printer for one '+name+' (reply with its name or number):\n'+'\n'.join(f'{i}. {label}' for i,label in enumerate(labels,1))


def follow_up(prompt,history):
    if len(history)<2:return prompt
    user,assistant=history[-2:]
    if user.get('role')!='user' or assistant.get('role')!='assistant':return prompt
    previous=intent(user.get('content'))
    if not previous or previous['printer']:return prompt
    name=previous['kind'].replace('-',' ')
    message=assistant.get('content','')
    labels=[]
    for index,line in enumerate(message.splitlines()[1:],1):
        prefix=f'{index}. '
        if not line.startswith(prefix):return prompt
        labels.append(line[len(prefix):])
    if not labels or message!=printer_menu(name,labels):return prompt
    for index,label in enumerate(labels,1):
        if prompt.strip().casefold() in (str(index),label.casefold()):
            return 'print a '+name+' on '+label
    return prompt


def generate():
    for path in (Path(__file__).resolve().parents[1]/'core',Path.home()/'.local/share/future-crash-look/core'):
        if (path/'fabric_client.py').is_file():sys.path.insert(0,str(path));break
    import fabric_client
    result=fabric_client.infer([
        {'role':'system','content':'Write one original fortune-cookie fortune. Warm, witty or quietly poetic. Return ONLY the fortune: one sentence, 30 to 55 ASCII characters. No heading, quotes, numbers, explanation or commands. Do not promise money, medical outcomes or certain predictions.'},
        {'role':'user','content':'A fresh little fortune for a printed Museum keepsake.'}],owner='look-fortune',priority='interactive',latency=True,think=False,options={'num_predict':70,'temperature':.9},timeout=45)
    value=' '.join(str((result.get('message') or {}).get('content') or '').strip().strip('"').split())
    if not 10<=len(value)<=90 or any(ord(c)<32 or ord(c)>126 for c in value):raise ValueError('The model did not return a short usable fortune. Nothing printed; ask again.')
    return value


def execute(prompt,allowed=True,pending=None):
    request=intent(prompt)
    if request is None:return None
    if not allowed:raise ValueError('This access profile cannot print. Use the workspace profile.')
    import printing
    rows=printing.destinations().get('printers',[])
    wanted=request['printer'].casefold()
    if not wanted:
        labels=[row['label'] for row in rows]
        if not labels:return 'No Fabric printers are available for a fortune.'
        name=request['kind'].replace('-',' ')
        command='print me a '+name+' on '
        labels.sort(key=lambda label:label.casefold()!='tiny printer')
        choices={str(index):command+label for index,label in enumerate(labels,1)}
        if pending is not None:
            pending.update(choices)
            pending.update({label.casefold():command+label for label in labels})
        return printer_menu(name,labels)
    matches=[row for row in rows if ' '.join(row['label'].casefold().split())==wanted]
    if len(matches)!=1:raise ValueError('No unique printer named '+request['printer']+'. Available: '+', '.join(row['label'] for row in rows)+'. Nothing printed.')
    label=matches[0]['label']
    value=generate()
    result=json.loads(printing.run_tool('print_design',{'kind':request['kind'],'text':value,'queue':label,'send':True},Path.home(),'print a '+request['kind'].replace('-',' ')+' on '+label,{}))
    deadline=time.monotonic()+40
    while result.get('state') in {'submitting','printing'} and time.monotonic()<deadline:
        time.sleep(1)
        try:checked=printing.request('inspect',result.get('node','local'),ident=result['id'])
        except (OSError,RuntimeError,ValueError) as error:raise RuntimeError('Could not verify job '+result['id']+'. Check printer jobs before retrying; delivery is unknown. '+str(error)) from error
        result=dict(checked,destination=label,design=result.get('design',{}))
    summary=printing.design_summary(result)
    if result.get('state') not in {'queued','submitting','printing'}:raise RuntimeError(summary)
    return summary
