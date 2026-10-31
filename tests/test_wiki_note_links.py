from pathlib import Path
from unittest.mock import Mock
import pytest
import wiki
import wiki_links
import wiki_online
import notebook
from notebook_core import Notebook
from notebook_markdown import extract_links,render
from test_media_request_regressions import lk


def test_wiki_reference_roundtrip_preserves_source_and_unicode(tmp_path):
    target=wiki_links.target('Ancient_Rome (日本語)',node='library-owner',archive='wikipedia_en_2026.zim')
    parsed=wiki_links.parse(target)
    assert parsed=={'title':'Ancient_Rome (日本語)','source':'saved','node':'library-owner','archive':'wikipedia_en_2026.zim'}
    text=notebook.make_link('Roman research',target)
    assert extract_links(text)==[('Roman research',target)]
    store=Notebook(tmp_path);row=store.create(text)
    kind,value=notebook.resolve_link(store,row,target)
    assert kind=='wiki' and value==target
    assert notebook.link_fields('wiki:Ancient_Rome')==('wiki:Ancient_Rome','Ancient Rome')


@pytest.mark.parametrize('target',['wiki:','wiki://evil/Article','wiki:Title?source=other','wiki:Title?node=../../bad','wiki:Title?archive=../../archive.zim','wiki:Bad%1bTitle','wiki:Title?source=live&node=owner','wiki:Title?source=live&source=saved','wiki:Title?unexpected=yes'])
def test_wiki_reference_rejects_ambiguous_or_unsafe_context(target):
    with pytest.raises(ValueError):wiki_links.parse(target)
    with pytest.raises(ValueError):notebook.link_target(target)


def test_note_opens_terminal_reader_with_literal_argv(monkeypatch):
    launch=Mock();monkeypatch.setattr(notebook.subprocess,'run',launch)
    target=wiki_links.target('Title $(never execute)',live=True)
    notebook.open_link('wiki',target)
    args=launch.call_args.args[0]
    assert args[-3:]==['wiki','--open-link',target]
    assert Path(args[1]).name=='lk'
    assert launch.call_args.kwargs=={'check':True}


def test_wiki_cli_preserves_explicit_saved_or_live_reference(monkeypatch):
    monkeypatch.setattr(wiki.media_storage,'settings',lambda:{'node':'default-owner'})
    desk=Mock(return_value=0);monkeypatch.setattr(wiki,'desk',desk)
    saved=wiki_links.target('Latin',node='library-owner',archive='edition.zim')
    assert wiki.main(['--open-link',saved],ui='ui')==0
    assert desk.call_args.args==('ui','library-owner')
    assert desk.call_args.kwargs['reference']['archive']=='edition.zim'
    live=wiki_links.target('Latin',live=True)
    assert wiki.main(['--open-link',live],ui='ui')==0
    assert desk.call_args.kwargs['live'] is True


def terminal(monkeypatch):
    import termios,tty
    class Terminal:
        def fileno(self):return 0
        def isatty(self):return True
    monkeypatch.setattr(wiki.sys,'stdin',Terminal())
    monkeypatch.setattr(termios,'tcgetattr',lambda fd:[])
    monkeypatch.setattr(termios,'tcsetattr',lambda *a:None)
    monkeypatch.setattr(tty,'setcbreak',lambda fd:None)


def test_linked_live_article_escape_returns_directly_without_archive_request(lk,monkeypatch):
    terminal(monkeypatch)
    saved=Mock(side_effect=AssertionError('Live reference does not contact a saved owner'))
    monkeypatch.setattr(wiki,'request',saved)
    article=Mock(return_value={'title':'Latin','path':'Latin','paragraphs':['Article'],'links':[]})
    monkeypatch.setattr(wiki_online,'article',article)
    keys=iter(['esc']);monkeypatch.setattr(lk,'_read_tty_key',lambda *a:next(keys))
    assert wiki.desk(lk,'local',live=True,reference=wiki_links.parse('wiki:Latin?source=live'))==0
    article.assert_called_once_with('Latin');saved.assert_not_called()


def test_missing_pinned_archive_does_not_open_a_different_source(lk,monkeypatch):
    terminal(monkeypatch)
    monkeypatch.setattr(wiki,'request',Mock(return_value={'root':'/reference','archives':[{'id':'different.zim','title':'Different'}],'jobs':[]}))
    with pytest.raises(ValueError,match='will not switch sources'):
        wiki.desk(lk,'owner',reference=wiki_links.parse('wiki:Latin?archive=missing.zim'))


def test_copy_article_link_keeps_the_saved_owner_and_edition(lk,monkeypatch):
    terminal(monkeypatch)
    def request(action='status',**kwargs):
        if action=='article':return {'title':'Latin','path':'Latin','paragraphs':['Article'],'links':[]}
        return {'root':'/reference','archives':[{'id':'edition.zim','title':'Saved Wikipedia'}],'jobs':[],'reader_installed':True}
    monkeypatch.setattr(wiki,'request',request)
    copy=Mock(return_value=True);monkeypatch.setattr(wiki.look_renderer,'copy_text',copy)
    keys=iter(['down','enter','c','esc','esc']);monkeypatch.setattr(lk,'_read_tty_key',lambda *a:next(keys))
    assert wiki.desk(lk,'library-owner')==0
    target=extract_links(copy.call_args.args[0])[0][1]
    assert wiki_links.parse(target)=={'title':'Latin','source':'saved','node':'library-owner','archive':'edition.zim'}
