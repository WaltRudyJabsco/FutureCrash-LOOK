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


@pytest.mark.parametrize('kind',['fortune','fortune cookie'])
def test_exact_user_request_discovers_draws_submits_once(monkeypatch,lk,capsys,kind):
    monkeypatch.setattr(lk,'_cognition_module',lambda:cognition)
    listing=Mock(return_value={'printers':[{'label':'Tiny Printer'}]});monkeypatch.setattr(printing,'destinations',listing)
    import sys
    infer=Mock(side_effect=AssertionError('Default fortunes must not call a model'))
    monkeypatch.setitem(sys.modules,'fabric_client',Mock(infer=infer))
    submit=Mock(return_value=json.dumps({'state':'queued','id':'abc','destination':'Tiny Printer','design':{'kind':'fortune'}}));monkeypatch.setattr(printing,'run_tool',submit)
    result=lk._lo_fortune_direct('print me a '+kind+' on tiny printer','workspace')
    assert 'sent to Tiny Printer' in result and 'abc' in result
    listing.assert_called_once();infer.assert_not_called();submit.assert_called_once()
    assert submit.call_args.args[1]['text'] is None
    assert submit.call_args.args[1]['kind']==kind.replace(' ','-')
    assert submit.call_args.args[1]['queue']=='Tiny Printer' and submit.call_args.args[1]['send'] is True
    assert 'sent' in capsys.readouterr().out


def test_failure_stops_before_printing_and_reports_reason(monkeypatch,lk):
    monkeypatch.setattr(lk,'_cognition_module',lambda:cognition)
    monkeypatch.setattr(printing,'destinations',lambda:{'printers':[{'label':'Tiny Printer'}]})
    submit=Mock(side_effect=ValueError('Deck unavailable'));monkeypatch.setattr(printing,'run_tool',submit)
    assert 'Deck unavailable' in lk._lo_fortune_direct('print me a fortune on tiny printer','workspace')
    submit.assert_called_once()


def test_available_printers_bare_phrase(lk,monkeypatch):
    monkeypatch.setattr(printing,'request',lambda *a:{'printers':[]})
    assert 'No configured' in lk._lo_printers_direct('available printers')


def test_read_only_profile_never_generates(lk,monkeypatch):
    monkeypatch.setattr(lk,'_cognition_module',lambda:cognition)
    submit=Mock();monkeypatch.setattr(printing,'run_tool',submit)
    assert 'cannot print' in lk._lo_fortune_direct('print me a fortune on Tiny Printer','conservative')
    submit.assert_not_called()


def test_direct_waits_for_background_failure(monkeypatch):
    monkeypatch.setattr(printing,'destinations',lambda:{'printers':[{'label':'Tiny Printer'}]})
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


def test_signal_fortune_menu_and_typo(monkeypatch):
    monkeypatch.setattr(printing,'destinations',lambda:{'printers':[{'label':'Brother'},{'label':'Tiny Printer'}]})
    menu=fortune.execute('/fortune')
    history=[{'role':'user','content':'/fortune'},{'role':'assistant','content':menu}]
    for reply in ('1','Tiny Printer'):
        assert fortune.follow_up(reply,history)=='print a fortune on Tiny Printer'
    assert fortune.intent('print a forutne on tiny printer')=={'printer':'tiny printer','kind':'fortune'}
    assert fortune.follow_up('1',history+[{'role':'assistant','content':'Something else'}])=='1'


def test_aphorism_deck_survives_reopen_and_wraps_without_repeats(tmp_path):
    import sqlite3,fortune_deck
    path=tmp_path/'jobs.db'
    lines=[]
    for _ in range(len(fortune_deck.LINES)+1):
        with sqlite3.connect(path) as db:lines.append(fortune_deck.draw(db))
        db.close()
    assert len(set(lines[:-1]))==len(fortune_deck.LINES) and lines[-1]==lines[0]
    assert all(line.isascii() and len(line)<=90 for line in lines)


def test_changed_deck_size_preserves_existing_cursor(tmp_path):
    import sqlite3,fortune_deck
    with sqlite3.connect(tmp_path/'jobs.db') as db:
        db.execute('CREATE TABLE cookie_deck (id INTEGER PRIMARY KEY, position INTEGER NOT NULL)')
        db.execute('INSERT INTO cookie_deck VALUES (1,10000)');db.commit()
        assert fortune_deck.draw(db)==fortune_deck.LINES[10000%len(fortune_deck.LINES)]


def test_concurrent_clients_draw_unique_cards(tmp_path):
    import sqlite3,fortune_deck
    from concurrent.futures import ThreadPoolExecutor
    path=tmp_path/'jobs.db'
    def draw(_):
        with sqlite3.connect(path,timeout=10) as db:return fortune_deck.draw(db)
    with ThreadPoolExecutor(max_workers=4) as pool:rows=list(pool.map(draw,range(24)))
    assert len(set(rows))==24
