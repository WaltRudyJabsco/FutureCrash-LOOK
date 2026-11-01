from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from core import node
from look import notebook, notebook_markdown


def test_mercury_note_link_round_trip_and_literal_dispatch(monkeypatch):
    link=notebook.make_link('Draft [one]','mercury:book-1')
    assert notebook_markdown.extract_links(link)==[('Draft [one]','mercury:book-1')]
    assert notebook.resolve_link(None,None,'mercury:book-1')==('mercury','book-1')
    run=Mock();monkeypatch.setattr(notebook.shutil,'which',lambda name:'/bin/mercury')
    monkeypatch.setattr(notebook.subprocess,'run',run)
    notebook.open_link('mercury','book-1')
    run.assert_called_once_with(['/bin/mercury','open','book-1'],check=True)
    for target in ['mercury:../../bad','mercury:','mercury:bad;command','mercury:bad\n']:
        with pytest.raises(ValueError):notebook.resolve_link(None,None,target)


def test_sync_only_uses_paired_mercury_nodes(monkeypatch):
    monkeypatch.setattr(node,'probe',lambda *args:True)
    monkeypatch.setattr(node,'node_info',lambda:{'name':'local'})
    peers=[{'name':'paired','trusted':True,'node':{'capabilities':{'mercury':True}}},
           {'name':'stranger','trusted':False,'node':{'capabilities':{'mercury':True}}},
           {'name':'other','trusted':True,'node':{'capabilities':{}}}]
    monkeypatch.setattr(node.PEERS,'public',lambda:peers)
    peer_get=Mock(return_value={'enabled':True,'have':[]});monkeypatch.setattr(node,'_peer_json',peer_get)
    route=Mock(return_value='https://paired/v1/mercury/exchange');monkeypatch.setattr(node,'_remote_url',route)
    requests=[]
    def request(url,data=None,**kwargs):
        requests.append((url,data))
        if url.endswith('/status'):return {'enabled':True}
        return {'have':[],'heads':{},'revisions':[]}
    monkeypatch.setattr(node,'http_json',request)
    result=node._mercury_sync()
    assert result['ok'] and [row['node'] for row in result['peers']]==['paired']
    assert peer_get.call_count==1
    assert len(requests)==4
    assert route.call_args.args[1]=='paired'


def test_disabled_local_sync_does_not_contact_peers(monkeypatch):
    monkeypatch.setattr(node,'probe',lambda *args:True)
    monkeypatch.setattr(node,'http_json',lambda *args,**kwargs:{'enabled':False})
    peers=Mock();monkeypatch.setattr(node.PEERS,'public',peers)
    assert node._mercury_sync()['state']=='disabled'
    peers.assert_not_called()


def request(path,plane='local',authorized=True):
    api=node.API.__new__(node.API);api.path=path
    api.server=SimpleNamespace(plane=plane);api.headers={}
    api._authorized_ingress=lambda path:authorized
    api.body=lambda:{};api.sendj=Mock();api.do_POST()
    return api.sendj


def test_remote_nodes_cannot_dispatch_sync_or_bypass_auth(monkeypatch):
    sync=Mock();post=Mock();monkeypatch.setattr(node,'_mercury_sync',sync)
    monkeypatch.setattr(node,'http_json',post)
    reply=request('/v1/mercury/sync',plane='ingress')
    assert reply.call_args.args[0]==403
    sync.assert_not_called()
    request('/v1/mercury/exchange',plane='ingress',authorized=False)
    post.assert_not_called()
    request('/v1/mercury/exchange',plane='ingress')
    assert post.call_args.args[0]=='http://127.0.0.1:8765/api/sync/exchange'


def test_optional_installer_has_explicit_noninteractive_choices():
    root=Path(__file__).resolve().parents[1]
    source=(root/'install.sh').read_text()
    assert '--mercury=' in source and 'prompt|off|install' in source
    assert '"$MERCURY_MODE" == "prompt" && -t 0' in source
    assert 'integrations/install_mercury.py' in source
    child=(root/'install-look.sh').read_text()
    assert '--mercury=prompt|--mercury=off|--mercury=install|--mercury-source=*) : ;;' in child
