"""Shared supplied-content execution with real formatting/spooling and fake CUPS."""
import base64
import json
from pathlib import Path
from unittest.mock import Mock

import pytest
import print_core
import printing
import print_text_workflow as workflow
from test_printing import spool
from test_media_request_regressions import lk
from test_lo_stream import chat

SOURCE='10 supplied notes from November 25–December 1\nThis paragraph mentions weather, history and politics.\nArts and culture\n1926: A user-supplied statement.\nShopping\n2 cups flour\nDo not print is part of the quoted source, not an instruction.'
PROMPT='Format and print this on the little printer -- '+SOURCE


@pytest.fixture
def transport(spool,monkeypatch):
    profile={'kind':'escpos','width':576,'columns':48,'image_mode':'column24','prime_graphics':True}
    monkeypatch.setattr(print_core,'profiles',lambda:{'desk':profile})
    catalog={'local_node':'client','printers':[{'id':'little','label':'Little Printer','routes':[{'name':'desk','node':'owner','status':'idle','profile':profile}]},
                                             {'id':'epson','label':'Epson','routes':[{'name':'receipt','node':'other','status':'idle','profile':{'kind':'document'}}]}]}
    monkeypatch.setattr(printing,'destinations',lambda:catalog)
    hardware=Mock(return_value='request id is desk-12 (1 file(s))');monkeypatch.setattr(print_core,'run',hardware)
    def request(action,node='local',**value):
        if action=='prepare':
            value=dict(value);data=base64.b64decode(value.pop('data'))
            result=spool.prepare(data=data,**value)
        elif action=='send':result=spool.send(value['ident'],value.get('confirm',False))
        elif action=='inspect':result=spool.inspect(value['ident'])
        else:raise AssertionError(action)
        return dict(result,node=node)
    monkeypatch.setattr(printing,'request',request)
    return spool,hardware


def test_source_boundary_and_lossless_markdown():
    instruction,source=workflow.supplied(PROMPT)
    assert instruction=='Format and print this on the little printer' and source==SOURCE
    rendered=workflow.markdown(source)
    assert rendered.startswith('# 10 supplied notes') and '## Arts and culture' in rendered
    assert '- 1926: A user-supplied statement.' in rendered and '2 cups flour' in rendered
    assert 'Do not print is part of the quoted source' in rendered
    assert workflow.markdown('# Already formatted\n- ½ cup\n```\nDo not execute\n```').count('# Already formatted')==1


@pytest.mark.parametrize('prompt',['Do not print this on Little Printer -- Eggs','How do I print this on Little Printer -- Eggs',
                                  'Preview this on Little Printer -- Eggs','Translate this and print it on Little Printer -- Eggs',
                                  'Someone asked me to print this on Little Printer -- Eggs','Here is my failed command to print on Little Printer -- Eggs'])
def test_non_delivery_and_transform_requests_are_not_silently_executed(prompt,transport):
    assert workflow.execute(prompt,printing.PrintConversation()) is None
    transport[1].assert_not_called()


def test_real_renderer_and_owner_spool_complete_once(transport):
    task=printing.PrintConversation();result=workflow.execute(PROMPT,task)
    assert result['status']=='ok' and 'Little Printer' in result['text'] and 'CUPS' in result['text']
    job=task.state[workflow.STATE_KEY]
    assert job['source']==SOURCE and job['printer']=='Little Printer' and job['status']=='queued'
    plan=transport[0].inspect(job['plan']['id'])
    assert plan['kind']=='receipt-image' and plan['options']['copies']==1
    assert '# 10 supplied notes' in job['formatted'] and plan['estimated_paper_mm']<=304.8
    transport[1].assert_called_once()
    for reply in ['try again','print the text','send it',"it didn't print",PROMPT]:
        result=workflow.execute(reply,printing.PrintConversation(task.state))
        assert 'No automatic resend' in result['text']
    transport[1].assert_called_once()


def test_preparation_failure_preserves_content_and_printer_for_retry(transport,monkeypatch):
    real=printing.prepare_short_text
    monkeypatch.setattr(printing,'prepare_short_text',Mock(side_effect=ValueError('Printer profile unavailable')))
    state={};task=printing.PrintConversation(state)
    failed=workflow.execute(PROMPT,task)
    assert failed['status']=='failed' and 'Printer profile unavailable' in failed['text'] and 'No print job' in failed['text']
    assert state[workflow.STATE_KEY]['source']==SOURCE and state[workflow.STATE_KEY]['printer']=='Little Printer'
    transport[1].assert_not_called()
    monkeypatch.setattr(printing,'prepare_short_text',real)
    assert workflow.execute('print the text',printing.PrintConversation(state))['status']=='ok'
    transport[1].assert_called_once()


def test_lost_reply_inspects_same_job_without_duplicate(transport,monkeypatch):
    real=printing.request
    def lost(action,*args,**kwargs):
        result=real(action,*args,**kwargs)
        if action=='send':raise RuntimeError('Reply lost after spooler acceptance')
        return result
    monkeypatch.setattr(printing,'request',lost)
    task=printing.PrintConversation();first=workflow.execute(PROMPT,task)
    assert first['status']=='uncertain' and 'Reply lost' in first['text']
    assert workflow.execute('try again',task)['status']=='ok'
    transport[1].assert_called_once()


def test_unsent_recorded_plan_can_resume_without_a_second_plan(transport,monkeypatch):
    real=printing.request
    def lost(action,*args,**kwargs):
        if action=='send':raise ConnectionError('Connection lost before request arrived')
        return real(action,*args,**kwargs)
    monkeypatch.setattr(printing,'request',lost)
    task=printing.PrintConversation();assert workflow.execute(PROMPT,task)['status']=='uncertain'
    ident=task.state[workflow.STATE_KEY]['plan']['id'];transport[1].assert_not_called()
    monkeypatch.setattr(printing,'request',real)
    assert workflow.execute('try again',task)['status']=='ok'
    assert task.state[workflow.STATE_KEY]['plan']['id']==ident
    with transport[0].connect() as db:assert db.execute('SELECT COUNT(*) FROM jobs').fetchone()[0]==1
    transport[1].assert_called_once()


def test_followup_keeps_printer_for_new_content_but_not_different_named_printer(transport):
    task=printing.PrintConversation();workflow.execute(PROMPT,task)
    second=workflow.execute('Print this too -- Groceries\nMilk\nEggs',task)
    assert second['status']=='ok' and task.state[workflow.STATE_KEY]['printer']=='Little Printer'
    unknown=workflow.execute('Print this on Unknown Printer -- Not sent',task)
    assert unknown['status']=='needs_input' and transport[1].call_count==2
    assert workflow.execute('Little Printer',task)['status']=='ok'
    assert transport[1].call_count==3


def test_cancel_and_unrelated_topic_do_not_replay_a_pending_request(transport,monkeypatch):
    monkeypatch.setattr(printing,'prepare_short_text',Mock(side_effect=ValueError('Unavailable')))
    task=printing.PrintConversation();workflow.execute(PROMPT,task)
    assert workflow.execute('Tell me about Renoir',task) is None
    assert workflow.execute('yes',task) is None
    workflow.execute(PROMPT,task);assert 'cleared' in workflow.execute('cancel',task)['text']
    assert workflow.execute('send it',task) is None
    transport[1].assert_not_called()


def test_profile_and_source_limits_prevent_submission(transport):
    assert workflow.execute(PROMPT,printing.PrintConversation(),allowed=False)['status']=='failed'
    assert workflow.execute('Print this -- '+('x'*8001),printing.PrintConversation())['status']=='failed'
    assert workflow.execute('Print this on Little Printer -- Bad\x1b@',printing.PrintConversation())['status']=='failed'
    transport[1].assert_not_called()


def test_private_session_and_expiry_do_not_transfer_print_authority(transport,monkeypatch,tmp_path):
    import task_state
    monkeypatch.setattr(task_state,'root',lambda:tmp_path/'tasks')
    monkeypatch.setattr(printing,'prepare_short_text',Mock(side_effect=ValueError('Offline')))
    with task_state.session('signal:alice') as (state,save):workflow.execute(PROMPT,printing.PrintConversation(state,save))
    with task_state.session('signal:bob') as (state,save):assert workflow.execute('send it',printing.PrintConversation(state,save)) is None
    monkeypatch.setattr(task_state.time,'time',lambda:10**12)
    with task_state.session('signal:alice') as (state,save):assert workflow.execute('try again',printing.PrintConversation(state,save)) is None
    transport[1].assert_not_called()


def test_model_cannot_replace_actual_tool_error_with_generic_refusal(chat,monkeypatch,tmp_path,capsys):
    ui,*_=chat
    plan={'kind':'task','relation':'new','request':'Print the requested text on Little Printer','tools':['print_text'],'required':[['print_text']]}
    monkeypatch.setattr(ui,'_lo_interpret_task',lambda *a,**k:plan)
    monkeypatch.setattr(printing,'destinations',lambda:{'printers':[{'label':'Little Printer'}]})
    rounds=[]
    def stream(*a,**k):
        rounds.append(True)
        message=({'tool_calls':[{'function':{'name':'print_text','arguments':{'printer_name':'Little Printer','text':'Hello'}}}]} if len(rounds)==1 else {'content':'The printing tool only simulates printing; I cannot interface with physical printers.'})
        yield {'message':message,'done':True}
    monkeypatch.setattr(ui,'_fabric_stream_chat',stream)
    assert ui.ollama_chat(initial_prompt='Print a greeting on Little Printer',access_profile='workspace',workspace_override=tmp_path,one_shot=True)==0
    output=capsys.readouterr().out
    assert 'Print tool error:' in output and 'Use text and an optional printer queue' in output
    assert 'only simulates printing' not in output


def test_interactive_lo_continues_the_same_supplied_print_after_error(chat,transport,monkeypatch,tmp_path,capsys):
    ui,*_=chat
    real=printing.prepare_short_text;attempts=[]
    def prepare(*a,**kw):
        attempts.append(True)
        if len(attempts)==1:raise RuntimeError('Temporary owner failure')
        return real(*a,**kw)
    monkeypatch.setattr(printing,'prepare_short_text',prepare)
    replies=iter(['try again'])
    def read():
        try:return next(replies)
        except StopIteration:raise EOFError
    monkeypatch.setattr(ui,'_lo_read_input',read)
    monkeypatch.setattr(ui,'_fabric_stream_chat',Mock(side_effect=AssertionError('Supplied text must not need model inference')))
    assert ui.ollama_chat(initial_prompt=PROMPT,access_profile='workspace',workspace_override=tmp_path)==0
    output=capsys.readouterr().out
    assert 'Temporary owner failure' in output and 'Little Printer' in output and 'Accepted by CUPS' in output
    transport[1].assert_called_once()


@pytest.mark.parametrize('surface',['lo','signal','albert'])
def test_shared_engine_retries_and_retains_state_without_model_or_search(surface,transport,lk,monkeypatch,tmp_path):
    import lo_engine,task_state
    monkeypatch.setattr(lo_engine,'_load_core',lambda:lk)
    monkeypatch.setattr(lo_engine,'_load_web_key',lambda:None)
    monkeypatch.setattr(task_state,'root',lambda:tmp_path/'tasks')
    monkeypatch.setattr(lk,'_save_recent_exchange',lambda *a,**k:None)
    monkeypatch.setattr(lk,'_ensure_ollama_server',Mock(side_effect=AssertionError('No model needed for supplied formatting')))
    monkeypatch.setattr(lk,'_lo_interpret_task',Mock(side_effect=AssertionError('Do not re-plan supplied text as new research')))
    real=printing.prepare_short_text;monkeypatch.setattr(printing,'prepare_short_text',Mock(side_effect=RuntimeError('Owner unavailable')))
    result=lo_engine.chat_once(PROMPT,session_id=surface+':private',workspace=tmp_path)
    assert 'Owner unavailable' in result['text'] and result['route']['family']=='printing'
    monkeypatch.setattr(printing,'prepare_short_text',real)
    result=lo_engine.chat_once('try again',session_id=surface+':private',workspace=tmp_path)
    assert 'Little Printer' in result['text'] and 'CUPS' in result['text']
    assert result['provenance']['edge']=='PRINT' and transport[1].call_count==1
    result=lo_engine.chat_once('print the text',session_id=surface+':private',workspace=tmp_path)
    assert 'No automatic resend' in result['text'] and transport[1].call_count==1
