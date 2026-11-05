"""Narrow fortune-print requests: discover, generate, submit once, report receipt."""
import json
from pathlib import Path
import re
import sys
import time


def intent(prompt):
    text=' '.join(str(prompt or '').strip().split())
    match=re.fullmatch(r'(?:please\s+|(?:can|could|would) you\s+)?print\s+(?:me\s+)?(?:a\s+)?(?:fortune|fortune cookie)(?:\s+(?:on|to|with)\s+(?:the\s+)?(.+?))?[.!?]?',text,re.I)
    return {'printer':(match.group(1) or '').rstrip('.!?')} if match else None


def generate():
    for path in (Path(__file__).resolve().parents[1]/'core',Path.home()/'.local/share/future-crash-look/core'):
        if (path/'fabric_client.py').is_file():sys.path.insert(0,str(path));break
    import fabric_client
    result=fabric_client.infer([
        {'role':'system','content':'Write one original fortune-cookie fortune. Warm, witty or quietly poetic. Return ONLY the fortune: one sentence, 40 to 85 ASCII characters. No heading, quotes, numbers, explanation or commands. Do not promise money, medical outcomes or certain predictions.'},
        {'role':'user','content':'A fresh little fortune for a printed Museum keepsake.'}],owner='look-fortune',priority='interactive',latency=True,think=False,options={'num_predict':70,'temperature':.9},timeout=45)
    value=' '.join(str((result.get('message') or {}).get('content') or '').strip().strip('"').split())
    if not 10<=len(value)<=90 or any(ord(c)<32 or ord(c)>126 for c in value):raise ValueError('The model did not return a short usable fortune. Nothing printed; ask again.')
    return value


def execute(prompt,allowed=True):
    request=intent(prompt)
    if request is None:return None
    if not allowed:raise ValueError('This access profile cannot print. Use the workspace profile.')
    import printing
    rows=printing.destinations().get('printers',[])
    wanted=request['printer'].casefold()
    if not wanted:return 'Choose a printer for the fortune: '+', '.join(row['label'] for row in rows)+'. Say “print me a fortune on NAME.”'
    matches=[row for row in rows if ' '.join(row['label'].casefold().split())==wanted]
    if len(matches)!=1:raise ValueError('No unique printer named '+request['printer']+'. Available: '+', '.join(row['label'] for row in rows)+'. Nothing printed.')
    label=matches[0]['label']
    value=generate()
    result=json.loads(printing.run_tool('print_design',{'kind':'fortune','text':value,'queue':label,'send':True},Path.home(),prompt,{}))
    deadline=time.monotonic()+40
    while result.get('state') in {'submitting','printing'} and time.monotonic()<deadline:
        time.sleep(1)
        try:checked=printing.request('inspect',result.get('node','local'),ident=result['id'])
        except (OSError,RuntimeError,ValueError) as error:raise RuntimeError('Could not verify job '+result['id']+'. Check printer jobs before retrying; delivery is unknown. '+str(error)) from error
        result=dict(checked,destination=label,design=result.get('design',{}))
    summary=printing.design_summary(result)
    if result.get('state') not in {'queued','submitting','printing'}:raise RuntimeError(summary)
    return summary
