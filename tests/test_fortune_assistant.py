import json
from unittest.mock import Mock
import pytest
import fortune_assistant as fortune
import printing
from core import cognition
from test_media_request_regressions import lk

@pytest.mark.parametrize('prompt',['print me a fortune on tiny printer','Please print a fortune on Tiny Printer.','Can you print me a fortune on the Tiny Printer?'])
def test_explicit_intent(prompt):
    assert fortune.intent(prompt)['printer'].casefold()=='tiny printer'

@pytest.mark.parametrize('prompt',['do not print me a fortune on tiny printer','How do I print a fortune on Tiny Printer?','I tried print me a fortune on tiny printer','Tiny Printer','immediately','preview a fortune on Tiny Printer'])
def test_no_implicit_replay(prompt):assert fortune.intent(prompt) is None


def test_exact_user_request_discovers_generates_submits_once(monkeypatch,lk,capsys):
    monkeypatch.setattr(lk,'_cognition_module',lambda:cognition)
    listing=Mock(return_value={'printers':[{'label':'Tiny Printer'}]});monkeypatch.setattr(printing,'destinations',listing)
    generate=Mock(return_value='A small kindness will find its way back to you.');monkeypatch.setattr(fortune,'generate',generate)
    submit=Mock(return_value=json.dumps({'state':'queued','id':'abc','destination':'Tiny Printer','design':{'kind':'fortune'}}));monkeypatch.setattr(printing,'run_tool',submit)
    result=lk._lo_fortune_direct('print me a fortune on tiny printer','workspace')
    assert 'sent to Tiny Printer' in result and 'abc' in result
    listing.assert_called_once();generate.assert_called_once();submit.assert_called_once()
    assert submit.call_args.args[1]['queue']=='Tiny Printer' and submit.call_args.args[1]['send'] is True
    assert 'sent' in capsys.readouterr().out


def test_failure_stops_before_printing_and_reports_reason(monkeypatch,lk):
    monkeypatch.setattr(lk,'_cognition_module',lambda:cognition)
    monkeypatch.setattr(printing,'destinations',lambda:{'printers':[{'label':'Tiny Printer'}]})
    monkeypatch.setattr(fortune,'generate',Mock(side_effect=ValueError('Model unavailable; nothing printed')))
    submit=Mock();monkeypatch.setattr(printing,'run_tool',submit)
    assert 'Model unavailable' in lk._lo_fortune_direct('print me a fortune on tiny printer','workspace')
    submit.assert_not_called()


def test_available_printers_bare_phrase(lk,monkeypatch):
    monkeypatch.setattr(printing,'request',lambda *a:{'printers':[]})
    assert 'No configured' in lk._lo_printers_direct('available printers')


def test_read_only_profile_never_generates(lk,monkeypatch):
    monkeypatch.setattr(lk,'_cognition_module',lambda:cognition)
    generate=Mock();monkeypatch.setattr(fortune,'generate',generate)
    assert 'cannot print' in lk._lo_fortune_direct('print me a fortune on Tiny Printer','conservative')
    generate.assert_not_called()


def test_generator_validates_model_output(monkeypatch):
    import sys
    infer=Mock(return_value={'message':{'content':'A small kindness will find its way back to you.'}})
    monkeypatch.setitem(sys.modules,'fabric_client',Mock(infer=infer))
    assert fortune.generate().startswith('A small kindness')
    assert infer.call_args.kwargs['think'] is False
    infer.return_value={'message':{'content':'too long '*30}}
    with pytest.raises(ValueError,match='Nothing printed'):fortune.generate()


def test_direct_waits_for_background_failure(monkeypatch):
    monkeypatch.setattr(printing,'destinations',lambda:{'printers':[{'label':'Tiny Printer'}]})
    monkeypatch.setattr(fortune,'generate',lambda:'Kindness finds its way home.')
    monkeypatch.setattr(printing,'run_tool',lambda *a:json.dumps({'id':'a','node':'owner','state':'submitting'}))
    inspect=Mock(return_value={'id':'a','state':'failed','receipt':{'error':'Wake the printer; no print data sent'}})
    monkeypatch.setattr(printing,'request',inspect);monkeypatch.setattr(fortune.time,'sleep',lambda _:None)
    with pytest.raises(RuntimeError,match='Wake the printer'):fortune.execute('print me a fortune on tiny printer')
    inspect.assert_called_once_with('inspect','owner',ident='a')


@pytest.mark.parametrize(('words','kind'), [('fortune cookie','fortune-cookie'),('fortune','fortune')])
def test_request_preserves_layout_when_choosing_printer(words, kind, monkeypatch):
    monkeypatch.setattr(printing,'destinations',lambda:{'printers':[{'label':'Tiny Printer'}]})
    pending={}
    fortune.execute('print me a '+words,pending=pending)
    prompt='print me a '+words+' on Tiny Printer'
    assert pending['tiny printer']==prompt
    assert fortune.intent(prompt)=={'printer':'Tiny Printer','kind':kind}


def test_cookie_preview_needs_only_text_and_lucky_numbers(monkeypatch):
    import print_design
    monkeypatch.setattr(print_design,'museum_artwork',Mock(side_effect=AssertionError('unexpected artwork lookup')))
    result=printing.design('Small wonders await.',kind='fortune-cookie')
    assert result['lines']==['Small wonders await.']
    assert len(set(result['lucky_numbers']))==6
    assert 'artwork' not in result
