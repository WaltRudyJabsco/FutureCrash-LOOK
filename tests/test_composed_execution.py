"""A stalled native-tool model must still complete a researched delivery."""
import json
import pytest
import tool_workflow
from test_lo_stream import chat
from test_media_request_regressions import lk
from test_supplied_text_print import transport,spool

PLAN={'kind':'task','relation':'new','request':'Summarize the requested novel and print on Little Printer',
      'tools':['wikipedia','print_text'],'required':[['print_text']]}
SUMMARY='# Novel summary\n\nTwo families struggle with inherited guilt and the possibility of choosing a different life.\n\nSource: Wikipedia, Novel (novel).'


def test_recovery_is_structured_and_keeps_prerequisites():
    tools=[{'type':'function','function':{'name':name,'parameters':{'type':'object','properties':{}}}} for name in ['wikipedia','web_search','print_text','printers_list','remove_path']]
    selected=tool_workflow.execution_tools(PLAN,tools)
    assert {t['function']['name'] for t in selected}=={'wikipedia','web_search','print_text','printers_list'}
    packet=tool_workflow.recovery_payload({'messages':[{'role':'user','content':'Do this'},{'role':'tool','content':'A source result'}],'tools':selected},selected,PLAN,set())
    assert 'tools' not in packet and packet['format']['oneOf'] and packet['think'] is False
    with pytest.raises(ValueError):tool_workflow.recovery_message({'content':'<execute_tool>print_text(...)</execute_tool>'},selected)
    with pytest.raises(ValueError):tool_workflow.recovery_message({'content':json.dumps({'tool':'remove_path','arguments':{'path':'x'}})},selected)


@pytest.mark.parametrize('surface',['lo','signal','albert'])
def test_stalled_model_retrieves_reads_composes_and_prints_once(surface,chat,transport,monkeypatch,tmp_path):
    import lo_engine,task_state
    ui,*_=chat
    monkeypatch.setattr(lo_engine,'_load_core',lambda:ui)
    monkeypatch.setattr(lo_engine,'_load_web_key',lambda:None)
    monkeypatch.setattr(task_state,'root',lambda:tmp_path/'tasks')
    monkeypatch.setattr(ui,'_lo_interpret_task',lambda *a,**k:dict(PLAN))
    monkeypatch.setattr(ui,'_lo_goal',lambda prompt,route:ui._cognition_module().new_goal(prompt,route))
    reads=[]
    def wiki(query='',title=None):
        reads.append((query,title))
        return json.dumps({'source':'Wikipedia','articles':[{'title':title,'text':'Full source text about two families and moral choice.'}]} if title else {'results':[{'title':'Novel (novel)','description':'Novel by the requested author'}]})
    monkeypatch.setattr(ui,'_wikipedia_lookup',wiki)
    decisions=iter([
        {'content':'Would you like me to search and then print?'},
        {'content':json.dumps({'tool':'wikipedia','arguments':{'query':'Novel author'}})},
        {'content':json.dumps({'tool':'wikipedia','arguments':{'title':'Novel (novel)'}})},
        {'content':json.dumps({'tool':'print_text','arguments':{'text':SUMMARY,'queue':'Little Printer'}})},
        {'content':json.dumps({'tool':'blocked','reason':'Already sent.'})},
    ])
    rounds=[]
    def stream(payload,**kw):
        rounds.append(payload)
        if len(rounds)>1:
            assert payload.get('format') and 'tools' not in payload
            assert 'wikipedia' in json.dumps(payload['format'])
        yield {'message':next(decisions),'done':True}
    monkeypatch.setattr(ui,'_fabric_stream_chat',stream)
    result=lo_engine.chat_once('Summarize the novel and print it on Little Printer',session_id=surface+':test',workspace=tmp_path)
    assert 'Accepted by CUPS' in result['text'],result['text']
    assert reads==[('Novel author',None),('', 'Novel (novel)')]
    transport[1].assert_called_once()


def test_read_article_returns_content_and_explicit_truncation(lk,monkeypatch):
    monkeypatch.setattr(lk,'_http_json',lambda url:{'query':{'pages':{'42':{'title':'Novel (novel)','extract':'Plot\n'+('x'*13000)}}}})
    value=json.loads(lk._wikipedia_lookup(title='Novel (novel)'))
    article=value['articles'][0]
    assert article['text'].startswith('Plot') and len(article['text'])==12000 and article['truncated']
    assert article['url'].endswith('Novel_(novel)')


def test_missing_article_is_not_fabricated(lk,monkeypatch):
    monkeypatch.setattr(lk,'_http_json',lambda url:{'query':{'pages':{'-1':{'title':'Missing','missing':''}}}})
    assert json.loads(lk._wikipedia_lookup(title='Missing'))['articles']==[]


def test_fabric_planner_does_not_pin_another_nodes_local_model(lk,monkeypatch):
    payloads=[]
    monkeypatch.delenv('LOOK_OLLAMA_MODEL',raising=False)
    def stream(payload,**kw):
        payloads.append(payload)
        yield {'message':{'content':json.dumps(dict(PLAN,missing=[],question=''))},'done':True}
    monkeypatch.setattr(lk,'_fabric_stream_chat',stream)
    monkeypatch.setattr(lk,'_active_ollama_model',lambda:'machine-local-model')
    result=lk._lo_interpret_task('Print a summary',[],{},lk._lo_tools('workspace'),'unused','',True)
    assert result['tools']==PLAN['tools'] and payloads[0]['model']==''


@pytest.mark.parametrize('surface',['lo','signal','albert'])
def test_please_resumes_failed_research_delivery_with_printer_and_real_error(surface,chat,transport,monkeypatch,tmp_path):
    import lo_engine,task_state
    ui,*_=chat
    monkeypatch.setattr(lo_engine,'_load_core',lambda:ui)
    monkeypatch.setattr(lo_engine,'_load_web_key',lambda:None)
    monkeypatch.setattr(task_state,'root',lambda:tmp_path/'tasks')
    monkeypatch.setattr(ui,'_lo_goal',lambda prompt,route:ui._cognition_module().new_goal(prompt,route))
    seen=[]
    def interpret(prompt,history,state,*a,**k):
        seen.append((prompt,dict(state.get('brain_task',{}))))
        return dict(PLAN,relation='continue' if prompt=='please' else 'new')
    monkeypatch.setattr(ui,'_lo_interpret_task',interpret)
    reads=[]
    def wiki(query='',title=None):
        reads.append(query or title)
        if len(reads)==1:raise OSError('Reference provider temporarily offline')
        return json.dumps({'source':'Wikipedia','articles':[{'title':'Novel','text':'Two families and moral choice.'}]})
    monkeypatch.setattr(ui,'_wikipedia_lookup',wiki)
    decisions=iter([
        {'tool_calls':[{'function':{'name':'wikipedia','arguments':{'title':'Novel'}}}]},
        {'content':'The provider failed.'},
        {'content':json.dumps({'tool':'blocked','reason':'Wikipedia lookup failed: Reference provider temporarily offline'})},
        {'tool_calls':[{'function':{'name':'wikipedia','arguments':{'title':'Novel'}}}]},
        {'tool_calls':[{'function':{'name':'print_text','arguments':{'queue':'Little Printer','text':SUMMARY}}}]},
    ])
    monkeypatch.setattr(ui,'_fabric_stream_chat',lambda *a,**k:iter([{'message':next(decisions),'done':True}]))
    session=surface+':followup'
    result=lo_engine.chat_once('Summarize the novel and print it on Little Printer',session_id=session,workspace=tmp_path)
    assert 'Reference provider temporarily offline' in result['text']
    assert result['events'][-1]['status']=='incomplete'
    transport[1].assert_not_called()
    result=lo_engine.chat_once('please',session_id=session,workspace=tmp_path)
    assert seen[-1][1]['status']=='pending' and 'Little Printer' in seen[-1][1]['user']
    assert 'Accepted by CUPS' in result['text']
    transport[1].assert_called_once()


def test_model_without_native_calls_uses_guarded_json_protocol(chat,transport,monkeypatch,tmp_path,capsys):
    ui,*_=chat
    monkeypatch.setattr(ui,'_ollama_capabilities',lambda *a:['completion'])
    monkeypatch.setattr(ui,'_lo_interpret_task',lambda *a,**k:dict(PLAN,tools=['print_text']))
    monkeypatch.setattr(ui,'_lo_goal',lambda prompt,route:ui._cognition_module().new_goal(prompt,route))
    def stream(base,payload,**kw):
        assert payload['format']['oneOf'] and 'tools' not in payload
        yield {'message':{'content':json.dumps({'tool':'print_text','arguments':{'queue':'Little Printer','text':'# Greeting\nHello.'}})},'done':True}
    monkeypatch.setattr(ui,'_ollama_stream_chat',stream)
    assert ui.ollama_chat(initial_prompt='Print a greeting on Little Printer',host_override='http://127.0.0.1:11434',access_profile='workspace',workspace_override=tmp_path,one_shot=True)==0
    assert 'Accepted by CUPS' in capsys.readouterr().out
    transport[1].assert_called_once()


def test_blocker_is_receipt_truth_not_model_disclaimer():
    assert 'model stopped' in tool_workflow.blocked_result([])
    result=tool_workflow.blocked_result([{'tool':'wikipedia','result':'Wikipedia lookup failed: network timeout'}])
    assert 'network timeout' in result


def test_source_review_blocks_wrong_subject_then_delivers_corrected_draft(chat,transport,monkeypatch,tmp_path,capsys):
    ui,*_=chat
    monkeypatch.setattr(ui,'_lo_interpret_task',lambda *a,**k:dict(PLAN))
    monkeypatch.setattr(ui,'_lo_goal',lambda prompt,route:ui._cognition_module().new_goal(prompt,route))
    monkeypatch.setattr(ui,'_wikipedia_lookup',lambda query='',title=None:json.dumps({'edge':'WIKI','source':'Wikipedia','articles':[{'title':title or 'Unrelated game','text':'Two families and moral choice.'}]}))
    reviews=[]
    def review(request,text,sources,*a,**k):
        reviews.append((text,sources));return {'status':'ready' if len(reviews)>1 else 'revise','reason':'Search results concerned an unrelated game; read the novel article.'}
    monkeypatch.setattr(ui,'_lo_review_delivery',review)
    decisions=iter([
        {'tool_calls':[{'function':{'name':'wikipedia','arguments':{'query':'Novel summary'}}}]},
        {'tool_calls':[{'function':{'name':'print_text','arguments':{'text':'A fabricated plot','queue':'Little Printer'}}}]},
        {'content':json.dumps({'tool':'wikipedia','arguments':{'title':'Novel (novel)'}})},
        {'content':json.dumps({'tool':'print_text','arguments':{'text':SUMMARY,'queue':'Little Printer'}})},
    ])
    monkeypatch.setattr(ui,'_fabric_stream_chat',lambda *a,**k:iter([{'message':next(decisions),'done':True}]))
    state={}
    assert ui.ollama_chat(initial_prompt='Summarize the novel and print it on Little Printer',access_profile='workspace',workspace_override=tmp_path,one_shot=True,task_context=(state,lambda:None))==0
    assert len(reviews)==2 and reviews[1][0]==SUMMARY and state['brain_sources']['receipts']
    transport[1].assert_called_once()
    assert 'Accepted by CUPS' in capsys.readouterr().out


def test_review_prompt_requires_source_relevance_and_bounded_model_decision(lk,monkeypatch):
    payloads=[]
    def stream(payload,**kw):
        payloads.append(payload)
        yield {'message':{'content':'{"status":"revise","reason":"Wrong subject"}'},'done':True}
    monkeypatch.setattr(lk,'_fabric_stream_chat',stream)
    assert lk._lo_review_delivery('Summarize a novel','Wrong characters',['A different article'],'unused','',True)['status']=='revise'
    assert payloads[0]['model']=='' and 'sources' in payloads[0]['messages'][-1]['content']
    assert 'tool_calls' not in payloads[0] and payloads[0]['format']['properties']['status']['enum']==['ready','revise']
