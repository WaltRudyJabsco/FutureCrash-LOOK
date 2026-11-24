"""Terminal source selection and acquisition, without real downloads or readers."""
from unittest.mock import Mock
import json
import pytest
import books
from test_media_request_regressions import lk


def test_discovery_uses_shared_service_and_numeric_cursor(monkeypatch):
    request=Mock(return_value={'entries':[],'next_index':51,'cached':True})
    monkeypatch.setattr(books.fabric_files,'request',request)
    assert books.discover('search',query='Virginia Woolf',start_index=26)['cached']
    request.assert_called_once_with('/v1/books/discover',{'mode':'search','subject':'','query':'Virginia Woolf','start_index':26},timeout=books.DISCOVERY_TIMEOUT_SECONDS)


def test_service_failure_uses_local_cache_without_another_online_attempt(monkeypatch):
    monkeypatch.setattr(books.fabric_files,'request',Mock(side_effect=RuntimeError('503')))
    fallback=Mock(return_value={'entries':[],'warning':'Cached catalog'})
    monkeypatch.setattr(books.book_core,'discover',fallback)
    assert books.discover('popular')['warning']=='Cached catalog'
    fallback.assert_called_once_with('popular','',query='',start_index=1,page=True,cached=True)


def test_standalone_search_can_use_online_catalog_without_a_node(monkeypatch):
    monkeypatch.setattr(books.fabric_files,'request',Mock(side_effect=ConnectionRefusedError()))
    fallback=Mock(return_value={'entries':[]});monkeypatch.setattr(books.book_core,'discover',fallback)
    books.discover('search',query='Austen')
    fallback.assert_called_once_with('search','',query='Austen',start_index=1,page=True)


def test_acquisition_favorites_owned_book_without_downloading(monkeypatch):
    entry={'title':'Owned book','url':'https://www.gutenberg.org/ebooks/123.opds'}
    owned={'id':'hash','title':'Owned book','gutenberg_id':'123','node':'existing-owner','favorite':False}
    request=Mock();monkeypatch.setattr(books,'request',request)
    assert books.acquire_book(entry,{'entries':[owned]},'download-owner',favorite=True)==owned
    request.assert_called_once_with('favorite',node='existing-owner',id='hash',selected=True)


@pytest.fixture
def terminal(lk,monkeypatch):
    monkeypatch.setattr(books.termios,'tcgetattr',lambda fd:[])
    monkeypatch.setattr(books.termios,'tcsetattr',lambda *a:None)
    monkeypatch.setattr(books.tty,'setcbreak',lambda *a:None)
    monkeypatch.setattr(books.book_preview,'preview',lambda *a:([],None))
    class Input:
        def fileno(self):return 0
    monkeypatch.setattr(books.sys,'stdin',Input())
    return lk


@pytest.mark.parametrize('favorite',[False,True])
def test_slash_switches_source_pages_and_adds_to_selected_owner(terminal,monkeypatch,capsys,favorite):
    rows=[];calls=[]
    monkeypatch.setattr(books,'catalog',lambda:{'entries':list(rows)})
    entry={'title':'New Gutenberg Book','author':'A Writer','url':'https://www.gutenberg.org/ebooks/123.opds'}
    discover=Mock(side_effect=[{'entries':[entry],'next_index':26,'warning':'Browsing cached catalog'},{'entries':[],'next_index':None}])
    monkeypatch.setattr(books,'discover',discover)
    def request(action,**kwargs):
        calls.append((action,kwargs))
        if action=='fetch':
            row={'id':'book-hash','title':entry['title'],'node':'library-owner','gutenberg_id':'123'}
            rows.append(row);return {'book':dict(row),'node':'library-owner'}
        if action=='favorite':rows[0]['favorite']=True;return {'ok':True}
        raise AssertionError(action)
    monkeypatch.setattr(books,'request',request)
    monkeypatch.setattr(books.look_renderer,'prompt_line',lambda *a,**kw:('y',False))
    keys=iter(['/','tab','N','e','w','enter','n','f' if favorite else 'enter','esc'])
    monkeypatch.setattr(terminal,'_read_tty_key',lambda *a:next(keys))
    assert books.desk(terminal,owner='library-owner')==0
    assert discover.call_args_list[0].args==('search','')
    assert discover.call_args_list[0].kwargs=={'query':'New','start_index':1}
    assert discover.call_args_list[1].kwargs['start_index']==26
    assert calls[0]==('fetch',{'node':'library-owner','url':entry['url']})
    assert len(calls)==(2 if favorite else 1)
    if favorite:assert calls[1]==('favorite',{'node':'library-owner','id':'book-hash','selected':True})
    output=capsys.readouterr().out
    assert 'SEARCH Gutenberg' in output and 'Browsing cached catalog' in output
    assert 'Saved to Favorites' in output if favorite else 'Book added to library on library-owner' in output


def test_cancelled_download_never_fetches(terminal,monkeypatch):
    monkeypatch.setattr(books,'catalog',lambda:{'entries':[]})
    monkeypatch.setattr(books,'discover',lambda *a,**k:{'entries':[{'title':'Book','url':'https://www.gutenberg.org/ebooks/123.opds'}]})
    answers=iter([('p',False),('n',False)])
    monkeypatch.setattr(books.look_renderer,'prompt_line',lambda *a,**k:next(answers))
    request=Mock();monkeypatch.setattr(books,'request',request)
    keys=iter(['d','enter','esc','esc']);monkeypatch.setattr(terminal,'_read_tty_key',lambda *a:next(keys))
    assert books.desk(terminal,owner='chosen-owner')==0
    request.assert_not_called()


def test_cli_search_preserves_paging_and_cache_notice(monkeypatch,capsys):
    search=Mock(return_value={'entries':[{'title':'Book'}],'next_index':26,'warning':'Cached catalog'})
    monkeypatch.setattr(books,'discover',search)
    assert books.main(['search','Woolf','--node','chosen-owner','--start-index','1','--json'],object())==0
    value=json.loads(capsys.readouterr().out)
    assert value['next_index']==26 and value['warning']=='Cached catalog'
    search.assert_called_once_with('search',query='Woolf',start_index=1)


@pytest.mark.parametrize('width',[56,72,100,140])
def test_final_frame_preserves_all_wrapped_command_rows(terminal,monkeypatch,width):
    import io,os
    class Output(io.StringIO):
        def isatty(self):return True
    monkeypatch.setattr(books.sys,'stdout',Output())
    monkeypatch.setenv('LOOK_NATIVE_PREVIEW','off')
    monkeypatch.setattr(terminal.shutil,'get_terminal_size',lambda *a:os.terminal_size((width,30)))
    monkeypatch.setattr(books,'catalog',lambda:{'entries':[{'id':'fixture','title':'Fixture book','node':'owner'}]})
    monkeypatch.setattr(terminal,'_read_tty_key',lambda *a:'esc')
    frames=[];render=terminal._terminal_frame_payload
    def capture(frame):frames.append(frame);return render(frame)
    monkeypatch.setattr(terminal,'_terminal_frame_payload',capture)
    assert books.desk(terminal,owner='owner')==0
    frame=terminal._strip_ansi(frames[-1])
    for label in ['f favorite','g Gutenberg','d discover','Esc back','? help']:
        assert label in frame,(width,label,frame)
    assert all(len(line)<=width for line in frame.splitlines())
    assert len(frame.splitlines())<=30
