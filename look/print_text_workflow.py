"""Lossless supplied-text formatting and session-scoped physical print delivery.

Source text is data, never a second instruction or a reason to search the web.
Only a current print request or an explicit continuation can deliver it.
"""
import re
from pathlib import Path

import printing

STATE_KEY='supplied_text_print'
MAX_HEADING_WORDS=12
TRANSFORMS=re.compile(r'\b(?:translate|summari[sz]e|rewrite|redact|fact.check|research|shorten)\b',re.I)
ACTION_START=re.compile(r'^(?:please\s+)?(?:(?:can|could|would|will) you\s+|i (?:want|need|would like)(?: you)? to\s+)?(?:please\s+)?(?:format|print|send|prepare)\b',re.I)
CONTINUATIONS={'try again','retry','print the text','print this text','print it','print it now',
               'send it','send it now','yes','y','confirmed','go ahead','please','immediately',
               "it didn't print",'it didnt print'}
NEW_COPY={'print another copy','print one more copy'}


def supplied(prompt):
    """Require an explicit instruction/data boundary, not a guessed prose body."""
    if not isinstance(prompt,str):return None
    match=re.search(r'\s+--\s+|\r?\n|:\s+',prompt)
    if not match:return None
    instruction=prompt[:match.start()].strip().rstrip(':')
    source=prompt[match.end():].strip()
    if not source or not ACTION_START.search(instruction) or TRANSFORMS.search(instruction):return None
    if not printing.explicit_print(instruction+' on requested destination','requested destination'):return None
    return instruction,source


def markdown(source):
    """Add structure without changing quantities, factual claims or quoted wording."""
    if any(ord(c)<32 and c not in '\r\n\t' for c in source):raise ValueError('Text contains terminal control characters')
    rows=[];in_code=False
    for position,line in enumerate(source.replace('\r\n','\n').splitlines()):
        stripped=line.strip()
        if stripped.startswith(('```','~~~')):in_code=not in_code;rows.append(line);continue
        if in_code or not stripped or re.match(r'^(?:#{1,6}\s|[-*+]\s|\d+[.)]\s|>)',stripped):rows.append(line);continue
        if re.match(r'^\d{3,4}:\s',stripped):rows.append('- '+stripped);continue
        short_heading=(len(stripped)<=100 and len(stripped.split())<=MAX_HEADING_WORDS
                       and not re.search(r'[.!?:;]$',stripped) and not re.match(r'^\d',stripped))
        title=position==0 and len(stripped)<=100 and not re.search(r'[.!?]$',stripped)
        heading=short_heading or title
        if heading:
            if rows and rows[-1]:rows.append('')
            rows.extend([('# ' if position==0 else '## ')+stripped,''])
        else:rows.append(line)
    result='\n'.join(rows).strip()
    if len(result)>printing.MAX_QUICK_TEXT:raise ValueError('Formatted text exceeds 8,000 characters; shorten it or use a reviewed document plan')
    return result


def execute(prompt,conversation,*,allowed=True,progress=None,events=None):
    """Return a host result, or None when this is a different kind of request."""
    state=conversation.state;job=state.get(STATE_KEY)
    parts=supplied(prompt);answer=' '.join(prompt.casefold().split()).strip(' .!?,')
    answer=answer.removeprefix('please ').removesuffix(' please').strip(' ,')
    calls=0
    def save():conversation.save()
    def report(text,status='ok'):return {'text':text,'status':status,'tool_calls':calls}
    def call(name,operation):
        nonlocal calls
        calls+=1
        if events:events.emit('tool_start',tool=name)
        try:result=operation()
        except Exception as exc:
            if events:events.emit('tool_end',tool=name,ok=False,error=str(exc))
            raise
        if events:
            events.emit('tool_done',tool=name,result=result)
            events.emit('tool_end',tool=name,ok=True)
        return result
    if job and answer in {'cancel','no','stop','never mind','nevermind'}:
        state.pop(STATE_KEY,None);save();return report('Print request cleared. No new job submitted.')
    if parts:
        instruction,source=parts
        if len(source)>printing.MAX_QUICK_TEXT:return report('No print job was submitted. Supplied text exceeds 8,000 characters; shorten it or use a reviewed document plan.','failed')
        repeated=(job and job.get('source')==source and job.get('instruction','').casefold()==instruction.casefold()
                  and job.get('status') in {'queued','submitting','printing','uncertain'})
        if not repeated:job={'instruction':instruction,'source':source,'status':'pending','printer':''}
        state[STATE_KEY]=job;save()
    elif job and answer in CONTINUATIONS|NEW_COPY:
        if answer in NEW_COPY:
            job={k:v for k,v in job.items() if k in {'instruction','source','printer'}}
            job['status']='pending';state[STATE_KEY]=job;save()
    elif job and (answer in job.get('choices',{}) or answer in {str(job.get('printer','')).casefold()}):
        choice=job.get('choices',{}).get(answer,job.get('printer'))
        job['printer']=choice;job['instruction']='Print the supplied text on '+choice;save()
    else:
        # Retain the printer preference, not stale execution authority.
        if job:state.pop(STATE_KEY,None);save()
        return None
    if not allowed:return report('This access profile cannot print. Use the workspace profile.','failed')
    try:
        if job['status'] in {'queued','submitting','printing','uncertain','failed'}:
            plan=job.get('plan')
            if not plan:return report('The previous print outcome is uncertain. Inspect printer jobs before retrying.','uncertain')
            result=call('printer_inspect',lambda:printing.request('inspect',plan['node'],ident=plan['id']))
            if result.get('state')!='prepared':
                result=dict(result,destination=job['printer']);job['result']=result;job['status']=result.get('state','uncertain');save()
                return report(printing.design_summary(result)+' No automatic resend.', 'ok' if result.get('state')=='queued' else 'uncertain')
            # Retry the same unsent plan, whose owner atomically prevents double-send.
            if progress:progress('Sending prepared job to '+job['printer']+'…')
            job['status']='uncertain';save()
            result=call('print_text',lambda:printing.request('send',plan['node'],ident=plan['id'],confirm=True))
        else:
            if progress:progress('Finding printer…')
            catalog=call('printers_list',printing.destinations)
            labels=[p['label'] for p in catalog.get('printers',[])]
            matches=[label for label in labels if printing.explicit_print(job['instruction'],label)]
            if len(matches)>1:raise ValueError('Choose one printer for this text')
            target=re.search(r'\b(?:on|to|using)\s+(?:the\s+)?(.+?)[.!?]*$',job['instruction'],re.I)
            named=target and target[1].strip().casefold() not in {'printer','the printer','it','that printer'}
            remembered=job.get('printer') or state.get('last_text_printer')
            printer=matches[0] if matches else remembered if not named and remembered in labels else None
            if not printer and not named:
                try:printer=printing.preferred_receipt(catalog=catalog)
                except ValueError:pass
            if not printer:
                job['choices']={str(i):label for i,label in enumerate(labels,1)}
                job['choices'].update({label.casefold():label for label in labels});save()
                return report('Choose a printer for the supplied text'+(' — requested destination was not found' if named else '')+':\n'+'\n'.join(f'{i}. {label}' for i,label in enumerate(labels,1)),'needs_input')
            job['printer']=printer;state['last_text_printer']=printer;save()
            if progress:progress('Formatting supplied text…')
            body=markdown(job['source']);job['formatted']=body;save()
            def submitting(plan):
                job['plan']={k:plan[k] for k in ['id','node']}
                job['status']='uncertain';save()
                if progress:progress('Sending to '+printer+'…')
            instruction='Print the supplied text on '+printer
            turn={'on_submit':submitting,'supplied_text':True}
            import json
            result=json.loads(call('print_text',lambda:printing.run_tool('print_text',{'queue':printer,'text':body},Path.home(),instruction,turn)))
        result=dict(result,destination=job['printer'])
        job['result']=result;job['status']=result.get('state','uncertain');save()
        status='ok' if result.get('state') in {'queued','submitting','printing'} else 'uncertain' if result.get('state')=='uncertain' else 'failed'
        return report(printing.design_summary(result),status)
    except (OSError,RuntimeError,ValueError,KeyError) as exc:
        job['error']=str(exc)
        if job.get('status')=='uncertain':
            save();plan=job.get('plan',{})
            return report('Print submission outcome is uncertain: '+str(exc)+'. Job '+str(plan.get('id','unknown'))+' on '+str(plan.get('node','owner'))+'. Inspect this job before another copy.','uncertain')
        job['status']='pending';save()
        return report('No print job was submitted. print_text: '+str(exc),'failed')
