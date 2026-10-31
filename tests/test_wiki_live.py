import base64
import io
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock
import pytest
import wiki
import wiki_online
import wiki_images
from notebook_markdown import cell_width
from test_media_request_regressions import lk


def test_link_colors_are_exact_anchors_and_hints_remain_optional():
    value=wiki.article_payload('<p>Latin is a word. Read <a href="Latin">Latin</a> here.</p>','Home','Home')
    assert value['paragraphs']==['Latin is a word. Read Latin here.']
    ui=SimpleNamespace(_c=lambda text,style:'<'+style+'>'+text+'</>')
    normal='\n'.join(wiki.article_lines(ui,value,100))
    assert normal.startswith('Latin is a word. Read <1;34>Latin</> here.')
    assert '[aa]' not in normal
    hints='\n'.join(wiki.article_lines(ui,value,100,True))
    assert '<1;33> [aa]</>' in hints
    assert value['rich_paragraphs'][0][1]=={'text':'Latin','code':'aa'}


def test_rich_wrapping_counts_cells_and_escapes_control_text():
    value={'rich_paragraphs':[[{'text':'日本語 Café ','code':'aa'},{'text':'plain \x1b]52;bad\a longlongword'}]],'paragraphs':[]}
    ui=SimpleNamespace(_c=lambda text,style:text)
    lines=wiki.article_lines(ui,value,12,True)
    assert all(sum(cell_width(c) for c in line)<=12 for line in lines)
    assert '\x1b' not in '\n'.join(lines)
    assert any('[aa]' in line for line in lines)


def test_live_images_use_wikimedia_hosts_and_archive_images_never_use_urls():
    html='<p><img width="24" src="//thumb.wikimedia.org/icon.png"><img width="300" resource="./File:Photo.jpg" src="//thumb.wikimedia.org/wikipedia/commons/thumb/a/ab/Photo.jpg/300px-Photo.jpg?utm_source=x" alt="Photo"><img src="https://evil.example/image.jpg"></p>'
    value=wiki.article_payload(html,'Page','Page',live=True)
    assert len(value['images'])==1
    assert value['images'][0]['source']=='https://commons.wikimedia.org/wiki/File:Photo.jpg'
    assert '?' not in value['images'][0]['url']
    saved=wiki.article_payload('<img src="../I/picture.png" width="100"><img src="https://evil.example/image.jpg">','A/Test','Test')
    assert saved['images']==[{'path':'I/picture.png','title':'picture.png'}]


@pytest.mark.parametrize('url',['http://en.wikipedia.org/wiki/Test','https://evil.example/image.png','https://en.wikipedia.org:8443/','https://u@en.wikipedia.org/'])
def test_live_network_cannot_redirect_to_private_or_arbitrary_hosts(url):
    with pytest.raises(ValueError):wiki_online.valid(url)
    with pytest.raises(ValueError):wiki_online.Redirects().redirect_request(None,None,302,'',{},url)


def test_live_cache_is_bounded_and_stale_content_is_labelled(tmp_path,monkeypatch):
    monkeypatch.setattr(Path,'home',lambda:tmp_path)
    now=[1000];monkeypatch.setattr(wiki_online.time,'time',lambda:now[0])
    fetch=Mock(return_value={'title':'Test'})
    first=wiki_online.cached('test','one',fetch)
    assert not first['cached']
    second=wiki_online.cached('test','one',fetch)
    assert second['cached'];fetch.assert_called_once()
    now[0]+=wiki_online.CACHE_SECONDS+1
    stale=wiki_online.cached('test','one',Mock(side_effect=OSError('no service')))
    assert stale['cached'] and stale['stale'] and 'cached' in stale['warning']
    with pytest.raises(RuntimeError,match='v selects'):wiki_online.cached('test','uncached',Mock(side_effect=OSError('offline')))


def test_saved_images_only_use_the_archive_rpc(tmp_path,monkeypatch):
    monkeypatch.setattr(Path,'home',lambda:tmp_path)
    monkeypatch.setattr(wiki_online,'read',Mock(side_effect=AssertionError('Saved mode must not fetch images online')))
    request=Mock(return_value={'mime':'image/png','data':base64.b64encode(b'png-data').decode()})
    monkeypatch.setattr(wiki,'request',request)
    path=wiki_images.image({'path':'I/Photo.png'},archive='test.zim',owner='owner')
    assert path.read_bytes()==b'png-data'
    request.assert_called_once_with('image',node='owner',archive='test.zim',query='I/Photo.png')
    assert wiki_images.image({'path':'I/Photo.png'},archive='test.zim',owner='owner')==path
    assert request.call_count==1


def test_online_cli_does_not_require_fabric_or_zim(monkeypatch,capsys):
    remote=Mock(side_effect=AssertionError('Live mode does not need an archive owner'))
    monkeypatch.setattr(wiki,'request',remote)
    search=Mock(return_value={'entries':[{'title':'Reef','path':'Reef'}]})
    monkeypatch.setattr(wiki_online,'search',search)
    assert wiki.main(['search','reef','--online','--json'])==0
    assert json.loads(capsys.readouterr().out)['entries'][0]['title']=='Reef'
    search.assert_called_once_with('reef');remote.assert_not_called()


def test_saved_cli_never_auto_switches_to_live(monkeypatch,capsys):
    live=Mock(side_effect=AssertionError('No implicit network requests'))
    monkeypatch.setattr(wiki_online,'article',live)
    request=Mock(return_value={'title':'Saved'})
    monkeypatch.setattr(wiki,'request',request)
    assert wiki.main(['article','Reef','--offline','--archive','test.zim','--json'])==0
    assert json.loads(capsys.readouterr().out)['title']=='Saved'
    live.assert_not_called()


def test_online_ui_can_search_color_links_view_images_and_switch_back(lk,tmp_path,monkeypatch,capsys):
    import termios,tty
    class Terminal:
        def fileno(self):return 0
        def isatty(self):return True
    monkeypatch.setattr(wiki.sys,'stdin',Terminal())
    monkeypatch.setattr(termios,'tcgetattr',lambda fd:[])
    monkeypatch.setattr(termios,'tcsetattr',lambda *a:None)
    monkeypatch.setattr(tty,'setcbreak',lambda fd:None)
    saved=Mock(return_value={'root':str(tmp_path),'archives':[],'jobs':[],'reader_installed':True})
    monkeypatch.setattr(wiki,'request',saved)
    monkeypatch.setattr(wiki.look_renderer,'prompt_line',lambda *a,**k:('Reef',False))
    monkeypatch.setattr(wiki_online,'search',Mock(return_value={'entries':[{'title':'Reef','path':'Reef'}]}))
    article=wiki.article_payload('<p>A <a href="Coral">coral</a> reef.</p>','Reef','Reef',live=True)
    monkeypatch.setattr(wiki_online,'article',Mock(return_value=article))
    gallery=Mock(return_value='No images');monkeypatch.setattr(wiki_images,'gallery',gallery)
    keys=iter(['/','enter','i','v','esc'])
    monkeypatch.setattr(lk,'_read_tty_key',lambda *a:next(keys))
    assert wiki.desk(lk,'owner',live=True)==0
    gallery.assert_called_once()
    assert gallery.call_args.kwargs['live'] is True
    saved.assert_called_once_with(node='owner')
    assert 'LIVE WIKIPEDIA' in capsys.readouterr().out


def test_live_entry_is_first_and_requires_selection(lk,tmp_path,monkeypatch,capsys):
    import termios,tty
    class Terminal:
        def fileno(self):return 0
        def isatty(self):return True
    monkeypatch.setattr(wiki.sys,'stdin',Terminal())
    monkeypatch.setattr(termios,'tcgetattr',lambda fd:[])
    monkeypatch.setattr(termios,'tcsetattr',lambda *a:None)
    monkeypatch.setattr(tty,'setcbreak',lambda fd:None)
    monkeypatch.setattr(wiki,'request',Mock(return_value={'root':str(tmp_path),'archives':[{'id':'saved.zim','title':'Saved English Wikipedia'}],'jobs':[],'reader_installed':True}))
    article=Mock(return_value={'title':'Live main page','paragraphs':['Live text'],'links':[]})
    monkeypatch.setattr(wiki_online,'article',article)
    keys=iter(['enter','esc','esc']);monkeypatch.setattr(lk,'_read_tty_key',lambda *a:next(keys))
    assert wiki.desk(lk,'owner')==0
    output=capsys.readouterr().out
    assert output.index('Live Wikipedia · web')<output.index('Saved English Wikipedia')
    article.assert_called_once_with('')


def test_unreachable_saved_owner_does_not_hide_live_entry(lk,monkeypatch,capsys):
    import termios,tty
    class Terminal:
        def fileno(self):return 0
        def isatty(self):return True
    monkeypatch.setattr(wiki.sys,'stdin',Terminal())
    monkeypatch.setattr(termios,'tcgetattr',lambda fd:[])
    monkeypatch.setattr(termios,'tcsetattr',lambda *a:None)
    monkeypatch.setattr(tty,'setcbreak',lambda fd:None)
    monkeypatch.setattr(wiki,'request',Mock(side_effect=OSError('owner unreachable')))
    live=Mock(side_effect=AssertionError('Opening the shelf must not contact Wikipedia'))
    monkeypatch.setattr(wiki_online,'article',live)
    monkeypatch.setattr(lk,'_read_tty_key',lambda *a:'esc')
    assert wiki.desk(lk,'owner')==0
    assert 'Live Wikipedia · web' in capsys.readouterr().out
    live.assert_not_called()


def test_no_picture_archive_does_not_start_image_workers():
    assert 'no-pictures archive' in wiki_images.gallery(None,0,{'images':[]})
