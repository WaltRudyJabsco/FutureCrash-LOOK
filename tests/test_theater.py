import io
import json
import threading
import urllib.request
import urllib.error
from http.server import ThreadingHTTPServer
from pathlib import Path
import pytest
from core import theater as t,theater_web as web

@pytest.fixture
def state(tmp_path,monkeypatch):
    monkeypatch.setattr(t,'root',lambda:tmp_path/'theater')
    monkeypatch.setattr(t,'start_guest',lambda:None)
    monkeypatch.setattr(t,'preparation',lambda media:{'state':'ready'})
    t.configure('https://theater.example:8443')
    return tmp_path


def test_ticket_scope_expiry_revoke_and_restart(state,monkeypatch):
    ticket=t.issue('movie1','Our movie',hours=1)
    assert t.view(ticket['code'])['media']=='movie1'
    assert ticket['code'] not in (t.root()/'theater.sqlite3').read_bytes().decode('latin1')
    assert 'digest' not in str(t.listing())
    original=t.time.time
    monkeypatch.setattr(t.time,'time',lambda:ticket['expires']+1)
    with pytest.raises(ValueError):t.admission(ticket['code'])
    monkeypatch.setattr(t.time,'time',original)
    t.revoke(ticket['id'])
    with pytest.raises(ValueError):t.admission(ticket['code'])

@pytest.mark.parametrize('hours',[0,-1,721,float('inf'),float('nan')])
def test_bad_lifetime(state,hours):
    with pytest.raises(ValueError):t.issue('movie','Title',hours=hours)


def test_channel_clock_and_ticketed_access(state,monkeypatch):
    now=[1000.0];monkeypatch.setattr(t.time,'time',lambda:now[0])
    ticket=t.issue(scope='channel')
    t.control('show','one','Movie one');now[0]+=20
    assert t.view(ticket['code'])['position']==20
    t.control('pause');now[0]+=30
    assert t.channel_state()['position']==20
    t.control('seek',position=100);t.control('resume');now[0]+=5
    assert t.channel_state()['position']==105
    with pytest.raises(ValueError):t.view()
    t.control('access',public=True);assert t.view()['media']=='one'
    t.control('stop')
    with pytest.raises(ValueError):t.view()
    assert t.view(ticket['code'])['state']=='stopped'


def test_media_is_resolved_from_catalog_before_grant(state):
    def entry(ident):raise FileNotFoundError('missing original')
    with pytest.raises(FileNotFoundError):t.admin({'action':'ticket','media':'/etc/passwd'},lambda:{},entry)
    assert t.listing()['tickets']==[]

@pytest.fixture
def server(state):
    srv=ThreadingHTTPServer(('127.0.0.1',0),web.Guest)
    srv.daemon_threads=True
    thread=threading.Thread(target=srv.serve_forever,daemon=True);thread.start()
    yield 'http://127.0.0.1:'+str(srv.server_port)
    srv.shutdown();srv.server_close()


def test_guest_admission_range_stream_and_no_admin_routes(server,monkeypatch):
    ticket=t.issue('movie1','Movie')
    with pytest.raises(urllib.error.HTTPError) as denied:urllib.request.urlopen(server+'/state')
    assert denied.value.code==403
    request=urllib.request.Request(server+'/admit',data=json.dumps({'code':ticket['code']}).encode(),headers={'Content-Type':'application/json'})
    with urllib.request.urlopen(request) as r:
        cookie=r.headers['Set-Cookie'];assert 'HttpOnly' in cookie and 'Secure' in cookie
    headers={'Cookie':cookie.split(';')[0]}
    with urllib.request.urlopen(urllib.request.Request(server+'/state',headers=headers)) as r:
        assert json.load(r)['media']=='movie1'
    calls=[]
    class Response(io.BytesIO):
        status=206
        headers={'Content-Type':'video/mp4','Content-Length':'4','Content-Range':'bytes 0-3/10'}
    def source(media,range_header,head):
        calls.append((media,range_header,head));return Response(b'test')
    monkeypatch.setattr(t,'media_request',source)
    with urllib.request.urlopen(urllib.request.Request(server+'/stream?path=/etc/passwd',headers={**headers,'Range':'bytes=0-3'})) as r:
        assert r.status==206 and r.read()==b'test'
    assert calls==[('movie1','bytes=0-3',False)]
    for path in ['/v1/theater','/api/theater','/etc/passwd']:
        with pytest.raises(urllib.error.HTTPError) as error:urllib.request.urlopen(server+path)
        assert error.value.code==404
    t.revoke(ticket['id'])
    with pytest.raises(urllib.error.HTTPError):urllib.request.urlopen(urllib.request.Request(server+'/stream',headers=headers))


def test_browser_assets_compile(state,tmp_path):
    import subprocess
    node='/Users/jreno/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node'
    if not Path(node).exists():pytest.skip('Node unavailable')
    from core import theater_admin_web
    for name,page in [('guest',web.PAGE),('admin',theater_admin_web.PAGE)]:
        script=page.split('<script>')[1].split('</script>')[0]
        path=tmp_path/(name+'.js');path.write_text(script)
        subprocess.run([node,'--check',str(path)],check=True,capture_output=True)


def test_node_admin_routes_and_owner_media_validation(state,monkeypatch):
    from core import node
    from types import SimpleNamespace
    handler=object.__new__(node.API)
    handler._file_target=lambda:(None,'/')
    handler.sendj=lambda code,data:(code,data)
    monkeypatch.setattr(node,'_local_media_catalog',lambda:{'entries':[dict(id='one',title='PCU',media_type='video/mp4')]})
    monkeypatch.setattr(node,'_local_media_entry',lambda ident:({'id':ident,'title':'PCU'},Path('/movie')))
    code,data=handler._theater_request({'action':'search','query':'PCU'})
    assert code==200 and data['items'][0]['id']=='one'
    code,data=handler._theater_request({'action':'ticket','media':'one'})
    assert code==200 and t.admission(data['code'])['media']=='one'


def test_assistant_tools_share_theater_actions(monkeypatch):
    import theater_desk
    calls=[]
    monkeypatch.setattr(theater_desk,'request',lambda value,node:(calls.append((value,node)) or {'ok':True}))
    theater_desk.run_tool('theater_lookup',{'node':'host','query':'PCU'})
    theater_desk.run_tool('theater_control',{'node':'host','action':'ticket','media':'one'})
    assert calls[0]==({'action':'search','query':'PCU'},'host')
    with pytest.raises(ValueError):theater_desk.run_tool('theater_control',{'action':'configure','url':'https://elsewhere'})


def test_post_dispatch_reaches_theater(state):
    from core import node
    import io
    from types import SimpleNamespace
    handler=object.__new__(node.API)
    handler.path='/v1/theater'
    handler.headers={'Content-Length':'19','Content-Type':'application/json'}
    raw=json.dumps({'action':'status'}).encode();handler.headers['Content-Length']=str(len(raw))
    handler.rfile=io.BytesIO(raw)
    handler._authorized_ingress=lambda path:True
    handler._theater_request=lambda data:('theater',data)
    assert handler.do_POST()==('theater',{'action':'status'})


def test_printable_ticket_qr_is_real_png(state):
    pytest.importorskip('qrcode.image.pure')
    ticket=t.issue('movie','PCU')
    image=t.qr_png(ticket['code'])
    assert image.startswith(b'\x89PNG\r\n\x1a\n') and len(image)>200


def test_guest_reports_preparation_without_blocking(server,monkeypatch):
    ticket=t.issue('pending','Movie')
    monkeypatch.setattr(t,'preparation',lambda media:{'state':'preparing'})
    headers={'Cookie':t.COOKIE+'='+ticket['code']}
    with urllib.request.urlopen(urllib.request.Request(server+'/state',headers=headers)) as response:
        assert json.load(response)['preparation']['state']=='preparing'
    with pytest.raises(urllib.error.HTTPError) as error:
        urllib.request.urlopen(urllib.request.Request(server+'/stream',headers=headers))
    assert error.value.code==425
