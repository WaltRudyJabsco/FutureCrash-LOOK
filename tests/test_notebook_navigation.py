import datetime as dt
import json
from unittest.mock import Mock

import pytest
from look import notebook
from look.notebook_core import Notebook, timestamp


@pytest.mark.parametrize('phrase,seconds',[('ten minutes',600),('10 minutes',600),('in ten minutes',600),
                                         ('a day',86400),('2 weeks',1209600)])
def test_reminder_duration_accepts_with_or_without_in(phrase,seconds):
    now=dt.datetime(2026,10,9,12).timestamp()
    assert timestamp(phrase,now)==now+seconds


def test_bare_clock_uses_next_local_occurrence_and_at_is_optional():
    now=dt.datetime(2026,10,9,12).timestamp()
    assert dt.datetime.fromtimestamp(timestamp('9am',now))==dt.datetime(2026,10,10,9)
    assert dt.datetime.fromtimestamp(timestamp('15:30',now))==dt.datetime(2026,10,9,15,30)
    assert timestamp('Saturday at 9am',now)==timestamp('Saturday 9am',now)


def test_title_filter_and_full_text_search_have_distinct_exclusion_scopes(tmp_path):
    store=Notebook(tmp_path)
    store.create('Scratch Pad\nHidden old discovery',project='LOOK')
    store.create('Other note\nNew discovery',project='Other')
    assert store.list('discovery',scope='title')==[]
    assert len(store.list('discovery',scope='all'))==2
    assert len(store.list(r'discovery \old',scope='all'))==1
    assert len(store.list(r'look \old',scope='title'))==1
    assert store.list(r'look \old',scope='all')==[]


def test_created_timestamp_survives_edits_and_sort_orders_are_deterministic(tmp_path,monkeypatch):
    import look.notebook_core as core
    clock=[1000]; monkeypatch.setattr(core.time,'time',lambda:clock[0])
    store=Notebook(tmp_path)
    first=store.create('Zulu',project='Alpha',due=5000)
    clock[0]=2000; store.create('Alpha',project='Zulu',kind='task')
    clock[0]=3000; store.change(first['note'],{'body':'Edited'})
    assert store.list(sort='updated')[0]['title']=='Zulu'
    assert store.list(sort='created')[0]['title']=='Alpha'
    assert store.list(sort='title')[0]['title']=='Alpha'
    assert store.list(sort='project')[0]['title']=='Zulu'
    assert store.list(sort='due')[0]['title']=='Zulu'
    assert store.list(sort='type')[0]['kind']=='note'
    assert store.list()[0]['created']==1000 and store.list()[0]['updated']==3000


def test_bare_title_reopens_existing_record_and_new_explicitly_duplicates(tmp_path,monkeypatch,capsys):
    store=Notebook(tmp_path)
    row=store.create('To Do\nOne task')
    monkeypatch.setattr(notebook,'Notebook',lambda:store)
    monkeypatch.setattr(notebook,'nudge_sync',lambda:None)
    monkeypatch.setattr(notebook.sys,'stdin',Mock(isatty=lambda:False))
    assert notebook.main(['To','Do','--json'])==0
    assert json.loads(capsys.readouterr().out)['id']==row['note']
    assert len(store.list())==1
    assert notebook.main(['new','To','Do'])==0
    assert len(store.list())==2
    assert notebook.main(['To','Do'])==1
    assert len(store.list())==2


def test_named_note_opens_editor_on_terminal(tmp_path,monkeypatch):
    store=Notebook(tmp_path); row=store.create('Scratch Pad')
    monkeypatch.setattr(notebook,'Notebook',lambda:store)
    monkeypatch.setattr(notebook.sys,'stdin',Mock(isatty=lambda:True))
    monkeypatch.setattr(notebook.sys,'stdout',Mock(isatty=lambda:True))
    editor=Mock(); monkeypatch.setattr(notebook,'edit',editor)
    assert notebook.main(['Scratch','Pad'])==0
    assert editor.call_args.args[1]['id']==row['note']
    assert len(store.list())==1
