import json
from threading import Event
from unittest.mock import Mock
import pytest
from look import note_composer as composer, notebook
from test_notebook_interaction import terminal

ROWS=[{'label':'Museum','target':'look:museum'}]

def test_validated_links_and_literal_prose():
    result=composer.validate({'parts':[{'text':'Explore '},{'link':0},{'text':'\n[bad](look:lock)\n```command\nrm -rf /\n```'}]},ROWS)
    assert notebook.make_link('Museum','look:museum') in result['body']
    assert len(notebook.extract_links(result['body']))==1

@pytest.mark.parametrize('parts',[[{'link':99}],[{'link':True}],[{'link':-1}],[{'text':3}],[]])
def test_invalid_ai_output(parts):
    with pytest.raises(ValueError):composer.validate({'parts':parts},ROWS)

def test_prompt_has_only_bounded_context_and_no_execution(monkeypatch):
    model=Mock(return_value={'message':{'content':json.dumps({'parts':[{'link':0}]})}})
    monkeypatch.setattr(composer,'infer',model)
    assert composer.draft('add museum','x'*10000,ROWS,Event())['body']==notebook.make_link('Museum','look:museum')
    sent=model.call_args.args[0][-1]['content']
    assert 'x'*composer.MAX_CONTEXT in sent and 'x'*(composer.MAX_CONTEXT+1) not in sent
    assert 'look:museum' in sent

def test_clarification():
    assert composer.validate({'question':'Which project?'},ROWS)=={'question':'Which project?'}

@pytest.mark.parametrize('entry',['[Museum](look:museum)',None])
def test_editor_insertion_at_cursor_and_cancel(entry,terminal,monkeypatch):
    make=Mock(return_value=entry);monkeypatch.setattr(notebook,'compose_entry',make)
    keys=iter(['left','\x07','\x13'])
    out=notebook.capture_note(5,lambda *args:next(keys),initial_text='ab')
    assert out=='a'+(entry or '')+'b'
    assert make.call_args.args[4]==1

def test_editor_failure_keeps_draft(terminal,monkeypatch):
    monkeypatch.setattr(notebook,'compose_entry',Mock(side_effect=OSError('offline')))
    keys=iter(['\x07','\x13'])
    assert notebook.capture_note(5,lambda *args:next(keys),initial_text='Keep me')=='Keep me'

def test_composer_clarifies_then_reviews(monkeypatch):
    capture=Mock(side_effect=['add my project','The blue one','Reviewed entry'])
    monkeypatch.setattr(notebook,'capture_note',capture)
    monkeypatch.setattr(composer,'candidates',lambda *a:(ROWS,''))
    generate=Mock(side_effect=[{'question':'Which one?'},{'body':'Draft entry'}])
    monkeypatch.setattr(composer,'draft',generate)
    assert notebook.compose_entry(None,5,lambda *a:'','old',1,['cooked'])=='Reviewed entry'
    assert 'The blue one' in generate.call_args.args[0]
    assert capture.call_args.kwargs['speech_state']==['cooked']

def test_mercury_catalog_failure_preserves_other_candidates(monkeypatch):
    monkeypatch.setattr(composer.urllib.request,'urlopen',Mock(side_effect=OSError('offline')))
    rows,warning=composer.candidates(None,notebook.action_catalog())
    assert len(rows)==24 and 'unavailable' in warning


def test_mercury_links_use_real_ids(monkeypatch):
    response=Mock();response.read.return_value=json.dumps({'projects':[{'project_id':'real-id','title':'Novel'},{'project_id':'../bad','title':'Bad'}]}).encode()
    context=Mock();context.__enter__=Mock(return_value=response);context.__exit__=Mock(return_value=False)
    monkeypatch.setattr(composer.urllib.request,'urlopen',Mock(return_value=context))
    rows,warning=composer.candidates(None,[])
    assert rows==[{'label':'Mercury: Novel','target':'mercury:real-id'}]
    assert not warning


def test_request_dictation_uses_original_terminal_state(terminal,monkeypatch):
    speech=Mock(return_value='Add Museum')
    monkeypatch.setattr(notebook,'dictate_for_editor',speech)
    keys=iter(['\x04','\x13'])
    assert notebook.capture_note(5,lambda *a:next(keys),assistant=False,speech_state=['cooked'])=='Add Museum'
    speech.assert_called_once_with(5,['cooked'])


def test_current_project_never_guessed(monkeypatch):
    infer=Mock(side_effect=AssertionError('Must clarify before inference'))
    monkeypatch.setattr(composer,'infer',infer)
    rows=[{'label':'Mercury: One','target':'mercury:one'},{'label':'Mercury: Two','target':'mercury:two'}]
    result=composer.draft('Add my current Mercury project','',rows,Event())
    assert 'question' in result and 'Mercury: One' in result['question'] and 'Mercury: Two' in result['question']
