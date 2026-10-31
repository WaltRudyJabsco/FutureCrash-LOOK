import io
import json
from pathlib import Path
from unittest.mock import Mock
import pytest
import wiki


@pytest.fixture
def home(tmp_path,monkeypatch):
    monkeypatch.setattr(Path,'home',lambda:tmp_path)
    return tmp_path


def test_reference_root_follows_local_media_and_can_be_changed(home):
    path=home/'.config/look/media_library.json';path.parent.mkdir(parents=True)
    path.write_text(json.dumps({'root':str(home/'storage/media')}))
    assert wiki.root()==home/'storage/media/reference'
    target=home/'external/Knowledge';wiki.local('configure',root=str(target))
    assert wiki.root()==target and target.is_dir()
    assert wiki.local()['archives']==[]


def test_catalog_parses_archive_size_and_flavour_without_arbitrary_urls(monkeypatch):
    feed=b'<feed xmlns="http://www.w3.org/2005/Atom"><entry><id>urn:uuid:a</id><title>Wikipedia</title><flavour>nopic</flavour><link type="application/x-zim" href="https://lb.download.kiwix.org/zim/test.zim.meta4" length="4096"/></entry><entry><id>bad</id><link type="application/x-zim" href="https://example.com/bad"/></entry></feed>'
    monkeypatch.setattr(wiki,'online',lambda url:io.BytesIO(feed))
    assert wiki.catalog()[0]['bytes']==4096 and wiki.catalog()[0]['flavour']=='nopic'
    assert len(wiki.catalog())==1


def test_metalink_requires_sha256_and_secure_mirrors(monkeypatch):
    body=b'<metalink xmlns="urn:ietf:params:xml:ns:metalink"><file name="test.zim"><size>12</size><hash type="sha-256">'+b'a'*64+b'</hash><url>https://mirror.example/test.zim</url></file></metalink>'
    monkeypatch.setattr(wiki,'online',lambda url:io.BytesIO(body))
    info=wiki.metalink('https://lb.download.kiwix.org/zim/test.zim.meta4')
    assert info['name']=='test.zim' and info['sha256']=='a'*64
    with pytest.raises(ValueError):wiki.metalink('https://example.com/test.zim.meta4')
    with pytest.raises(ValueError):wiki.metalink('http://lb.download.kiwix.org/zim/test.zim.meta4')
    body=body.replace(b'sha-256',b'md5')
    with pytest.raises(ValueError,match='SHA-256'):wiki.metalink('https://lb.download.kiwix.org/zim/test.zim.meta4')


def test_setup_is_fixed_confirmed_and_no_arbitrary_package(home,monkeypatch):
    with pytest.raises(PermissionError):wiki.start('setup')
    launch=Mock(return_value=Mock(pid=12345));monkeypatch.setattr(wiki.subprocess,'Popen',launch)
    value=wiki.start('setup',confirmed=True)
    assert launch.call_args.args[0][2:] == ['--job-worker',value['id']]
    assert launch.call_args.kwargs['stdin']==wiki.subprocess.DEVNULL
    assert launch.call_args.kwargs['start_new_session']


def test_article_links_stay_inside_archive_and_text_is_clean():
    parser=wiki.ArticleParser('A/Test')
    parser.feed('<h1>Test</h1><p>Café <a href="Other">other</a></p><script>bad()</script><a href="https://example.com">external</a><a href="../../escape">escape</a>')
    parser.flush()
    assert parser.links==[{'title':'other','path':'A/Other'}]
    assert not any('bad()' in text for text in parser.parts)


def test_cancelled_download_cannot_be_resurrected_by_progress(home):
    ident='a'*32;wiki.book_reader.write_json(wiki.job_path(ident),{'id':ident,'kind':'download','state':'downloading','created':0})
    wiki.local('cancel',id=ident)
    assert wiki.update(ident,state='downloading',bytes=100)['state']=='cancelled'


def test_download_resumes_and_verifies_rounded_catalog_size(home,monkeypatch):
    ident='b'*32;data=b'valid archive payload';sha=wiki.hashlib.sha256(data).hexdigest();folder=home/'references';folder.mkdir()
    partial=folder/('.look-wiki-'+sha[:16]+'.part');partial.write_bytes(data[:5])
    wiki.book_reader.write_json(wiki.job_path(ident),{'id':ident,'kind':'download','state':'queued','created':0,'root':str(folder),'entry':{'url':'metadata','bytes':1024}})
    monkeypatch.setattr(wiki,'metalink',lambda url:{'name':'test.zim','sha256':sha,'bytes':len(data),'url':'https://mirror/test.zim'})
    class Response(io.BytesIO):
        status=206;headers={'Content-Range':f'bytes 5-{len(data)-1}/{len(data)}'}
    requests=[]
    monkeypatch.setattr(wiki,'online',lambda url,headers:requests.append(headers) or Response(data[5:]))
    monkeypatch.setattr(wiki,'zim_call',lambda *args:{'ok':True})
    wiki.download(ident)
    assert requests==[{'Range':'bytes=5-'}]
    assert (folder/'test.zim').read_bytes()==data and not partial.exists()
    assert wiki.job(ident)['state']=='complete'


def test_invalid_checksum_does_not_publish_or_replace_archive(home,monkeypatch):
    ident='c'*32;folder=home/'references';folder.mkdir();partial=folder/('.look-wiki-'+'a'*16+'.part');partial.write_bytes(b'bad')
    wiki.book_reader.write_json(wiki.job_path(ident),{'id':ident,'kind':'download','state':'queued','created':0,'root':str(folder),'entry':{'url':'metadata','bytes':3}})
    monkeypatch.setattr(wiki,'metalink',lambda url:{'name':'test.zim','sha256':'a'*64,'bytes':3,'url':'https://mirror/test.zim'})
    with pytest.raises(ValueError,match='SHA-256'):wiki.download(ident)
    assert not (folder/'test.zim').exists() and partial.exists()
    with pytest.raises(ValueError):wiki.archive_path('../escape.zim')


def test_real_zim_creation_search_and_article(tmp_path):
    import subprocess
    python=wiki.state_root()/'venv/bin/python'
    if not python.is_file():pytest.skip('optional libzim reader unavailable')
    path=tmp_path/'fixture.zim'
    script='''
import sys
from libzim.writer import Creator,Item,StringProvider,Hint
class Page(Item):
 def __init__(self,path,title,text):super().__init__();self.path=path;self.title=title;self.text=text
 def get_path(self):return self.path
 def get_title(self):return self.title
 def get_mimetype(self):return 'text/html'
 def get_contentprovider(self):return StringProvider(self.text)
 def get_hints(self):return {Hint.FRONT_ARTICLE:True}
with Creator(sys.argv[1]).config_indexing(True,'eng') as writer:
 writer.set_mainpath('Home')
 writer.add_item(Page('Home','Knowledge','<h1>Knowledge</h1><p>Café coral reef research.</p><a href="Other">Other article</a>'))
 writer.add_item(Page('Other','Other article','<h1>Other</h1><p>More reef knowledge.</p>'))
'''
    subprocess.run([str(python),'-c',script,str(path)],check=True,capture_output=True,timeout=20)
    assert wiki.zim_call('verify',path)['articles']==2
    assert wiki.zim_call('search',path,'reef')['entries']
    assert wiki.zim_call('search',path,'Home')['entries'][0]['path']=='Home'
    article=wiki.zim_call('article',path,'Home')
    assert article['title']=='Knowledge' and 'Café coral reef research.' in article['paragraphs']
    assert article['links']==[{'title':'Other article','path':'Other'}]


from test_media_request_regressions import lk


def test_wiki_prompt_and_copy_use_renderer_without_lk_module_attribute(lk,tmp_path,monkeypatch):
    import termios,tty
    assert not hasattr(lk,'look_renderer')
    class Terminal:
        def fileno(self):return 0
        def isatty(self):return True
    monkeypatch.setattr(wiki.sys,'stdin',Terminal())
    monkeypatch.setattr(termios,'tcgetattr',lambda fd:[])
    monkeypatch.setattr(termios,'tcsetattr',lambda *a:None)
    monkeypatch.setattr(tty,'setcbreak',lambda fd:None)
    prompt=Mock(return_value=('n',False));monkeypatch.setattr(wiki.look_renderer,'prompt_line',prompt)
    copied=[];monkeypatch.setattr(wiki.look_renderer,'copy_text',lambda text:copied.append(text))
    def request(action='status',**kwargs):
        if action=='article':return {'title':'Test','paragraphs':['Offline text'],'links':[]}
        return {'root':str(tmp_path),'archives':[{'id':'test.zim','title':'Test','bytes':1}],'jobs':[]}
    monkeypatch.setattr(wiki,'request',request)
    keys=iter(['i','enter','y','esc','esc']);monkeypatch.setattr(lk,'_read_tty_key',lambda *a:next(keys))
    assert wiki.desk(lk,'local')==0
    assert prompt.call_count==1 and any('Offline text' in text for text in copied)


def test_source_wikipedia_links_are_local_only_for_the_matching_archive():
    parser=wiki.ArticleParser('mainPage',wiki_host='en.wikipedia.org')
    parser.feed('<a href="https://en.wikipedia.org/wiki/Ancient_Rome">Rome</a><a href="//en.wikipedia.org/wiki/Latin">Latin</a><a href="https://en.wikipedia.org/w/index.php?title=Arts">Arts</a><a href="https://elsewhere.example/wiki/Test">external</a><a href="https://en.wikipedia.org/wiki/../../escape">escape</a>')
    assert parser.links==[{'title':'Rome','path':'Ancient_Rome'},{'title':'Latin','path':'Latin'},{'title':'Arts','path':'Arts'}]
    other=wiki.ArticleParser('Home')
    other.feed('<a href="https://en.wikipedia.org/wiki/Latin">Latin</a>')
    assert other.links==[]


def test_wiki_can_search_from_linkless_landing_and_does_not_reinstall_reader(lk,tmp_path,monkeypatch,capsys):
    import termios,tty
    class Terminal:
        def fileno(self):return 0
        def isatty(self):return True
    monkeypatch.setattr(wiki.sys,'stdin',Terminal())
    monkeypatch.setattr(termios,'tcgetattr',lambda fd:[])
    monkeypatch.setattr(termios,'tcsetattr',lambda *a:None)
    monkeypatch.setattr(tty,'setcbreak',lambda fd:None)
    prompts=iter([('Latin',False),('',False)])
    monkeypatch.setattr(wiki.look_renderer,'prompt_line',lambda *a,**kw:next(prompts))
    calls=[]
    def request(action='status',**kwargs):
        calls.append((action,kwargs))
        if action=='article':return {'title':kwargs['query'] or 'mainPage','paragraphs':['Saved text'],'links':[]}
        if action=='search':return {'entries':[{'title':'Latin','path':'Latin'}]}
        return {'root':str(tmp_path),'reader_installed':True,'archives':[{'id':'test.zim','title':'Wikipedia','bytes':1}],'jobs':[]}
    monkeypatch.setattr(wiki,'request',request)
    keys=iter(['i','enter','/','esc','esc']);monkeypatch.setattr(lk,'_read_tty_key',lambda *a:next(keys))
    assert wiki.desk(lk,'owner')==0
    assert not any(action=='setup' for action,_ in calls)
    assert any(action=='article' and args['query']=='Latin' for action,args in calls)
    assert 'SAVED ARCHIVE' in capsys.readouterr().out


def test_wiki_owner_picker_switches_only_after_success(lk,tmp_path,monkeypatch):
    import termios,tty
    class Terminal:
        def fileno(self):return 0
        def isatty(self):return True
    monkeypatch.setattr(wiki.sys,'stdin',Terminal())
    monkeypatch.setattr(termios,'tcgetattr',lambda fd:[])
    monkeypatch.setattr(termios,'tcsetattr',lambda *a:None)
    monkeypatch.setattr(tty,'setcbreak',lambda fd:None)
    monkeypatch.setattr(wiki.fabric_files,'nodes',lambda:[wiki.fabric_files.Destination('library-owner','/')])
    monkeypatch.setattr(wiki.look_renderer,'prompt_line',lambda *a,**kw:('library-owner',False))
    seen=[]
    def request(action='status',node='local',**kwargs):
        seen.append(node)
        return {'root':str(tmp_path),'archives':[],'jobs':[],'reader_installed':True}
    monkeypatch.setattr(wiki,'request',request)
    keys=iter(['o','esc']);monkeypatch.setattr(lk,'_read_tty_key',lambda *a:next(keys))
    assert wiki.desk(lk,'local')==0
    assert seen==['local','library-owner']
