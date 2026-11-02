import json
from unittest.mock import Mock
import pytest
import book_assistant
from core import cognition
from test_media_request_regressions import lk

ROWS=[{'id':'alex','title':'Alexandria: A History and a Guide','author':'E. M. Forster','node':'owner','path':'/private/library/alex.epub','reading':{'chapter':2,'paragraph':4,'updated':50}}, {'id':'pride','title':'Pride and Prejudice','author':'Jane Austen','node':'owner'}]


@pytest.mark.parametrize('text,query',[("let's continue reading the Alexandria book",'Alexandria'),('Let’s continue reading the Alexandria book','Alexandria'),('Can you resume reading the book Pride and Prejudice?','Pride and Prejudice'),('please continue listening to Alexandria','Alexandria'),('read "The Book of Tea"','The Book of Tea'),('I want to start reading the Alexandria book','Alexandria')])
def test_conversational_book_requests(text,query):
    assert book_assistant.intent(text)=={'action':'resume','query':query}


@pytest.mark.parametrize('text',['read my notes','read the clipboard','read this aloud','continue with the plan','continue working on the project','read about Alexander','play music','resume music','resume playback'])
def test_non_book_requests_are_not_hijacked(text):assert book_assistant.intent(text) is None


def test_canonical_lookup_has_saved_progress_and_owner_link_without_filesystem_path():
    result=book_assistant.lookup('the Alexandria book',catalog={'entries':ROWS})
    assert result['status']=='matched' and result['entries'][0]['id']=='alex'
    assert result['entries'][0]['reading']['chapter']==2
    assert result['entries'][0]['reader_path']=='/reader?id=alex&target=owner&resume=1'
    assert 'path' not in result['entries'][0]
    assert 'chapter 3, paragraph 5' in book_assistant.describe(result)


def test_typos_are_suggestions_and_duplicate_replicas_keep_latest_progress():
    rows=[{'id':'great','title':'Alexander the Great','reading':{'updated':1}}, {'id':'great','title':'Alexander the Great','reading':{'updated':10}}, {'id':'other','title':'Unknown book'}]
    result=book_assistant.lookup('Alexandria',catalog={'entries':rows,'errors':[{'node':'offline'}]})
    assert result['status']=='suggestions' and len(result['entries'])==1
    assert result['entries'][0]['reading']['updated']==10
    assert 'choose' in book_assistant.describe(result).lower() and 'incomplete shelf' in book_assistant.describe(result)
    assert book_assistant.lookup('absent',catalog={'entries':ROWS})['status']=='no_match'


def test_lo_direct_uses_catalog_before_any_model_or_directory_search(monkeypatch,lk,capsys):
    result=book_assistant.lookup('Alexandria',catalog={'entries':ROWS})
    lookup=Mock(return_value=result);monkeypatch.setattr(book_assistant,'lookup',lookup)
    monkeypatch.setattr(lk,'_save_recent_exchange',Mock())
    monkeypatch.setattr(lk,'_ensure_ollama_server',Mock(side_effect=AssertionError('No model needed')))
    monkeypatch.setattr(lk,'_lo_download_direct',Mock(side_effect=AssertionError('Book lookup must be first')))
    monkeypatch.delenv('OLLAMA_HOST',raising=False)
    assert lk.ollama_chat(initial_prompt="let's continue reading the Alexandria book",one_shot=True,access_profile='workspace')==0
    lookup.assert_called_once_with('Alexandria')
    assert 'Alexandria: A History and a Guide' in capsys.readouterr().out


def test_lo_schema_and_cognition_expose_books_in_read_only_profiles(lk,monkeypatch):
    monkeypatch.setattr(lk,"_cognition_module",lambda:cognition)
    names={t['function']['name'] for t in lk._lo_tools('conservative')}
    assert {'books_shelf','books_lookup'}<=names
    route=lk._lo_cognition_route("let's continue reading the Alexandria book",use_openjev=False)
    assert route.primary=='books' and 'books_lookup' in route.allowed_tools
    assert cognition.ACTION_BY_NAME['books_lookup'].risk=='read'
    narrowed={t['function']['name'] for t in lk._lo_tools_for_route('conservative',route)}
    assert 'books_lookup' in narrowed


def test_machine_lo_bridge_reports_books_receipt_without_model(monkeypatch,lk):
    from look import lo_engine
    monkeypatch.setattr(lo_engine,'_load_core',lambda:lk)
    monkeypatch.setattr(lo_engine,'_load_web_key',lambda:None)
    original=book_assistant.lookup
    monkeypatch.setattr(book_assistant,'lookup',lambda query:original(query,catalog={'entries':ROWS}))
    monkeypatch.setattr(lk,'_save_recent_exchange',Mock())
    monkeypatch.setattr(lk,'_ensure_ollama_server',Mock(side_effect=AssertionError('No model required')))
    value=lo_engine.chat_once("let's continue reading the Alexandria book",profile='conservative')
    assert 'Alexandria: A History and a Guide' in value['text']
    assert value['receipts'][0]['edge']=='BOOKS'
    assert value['route']['family']=='books'


def test_multiple_titles_require_a_choice_instead_of_claiming_resume():
    result=book_assistant.lookup('Alexandria',catalog={'entries':ROWS+[{'id':'other','title':'Alexandria: Another History'}]})
    assert result['status']=='ambiguous' and len(result['entries'])==2
    assert 'choose' in book_assistant.describe(result).lower()
