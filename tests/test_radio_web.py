import io
import json
from unittest.mock import Mock
import pytest
from core import radio_web, node
from test_browser_fabric_views import load


@pytest.mark.parametrize('surface',['signal-window','albert'])
@pytest.mark.parametrize('path',['/ytr','/api/ytr','/api/ytr/audio?id=a','/api/ytr/config'])
def test_radio_requires_authorization(surface,path,monkeypatch):
    module=load(surface);handler=module.Handler.__new__(module.Handler)
    handler.path=path;handler._require_endpoint=Mock(return_value=False)
    gateway=Mock();monkeypatch.setattr(radio_web,'handle',gateway)
    handler.do_GET();handler._require_endpoint.assert_called_once_with('lo.use');gateway.assert_not_called()


@pytest.mark.parametrize('surface',['signal-window','albert'])
def test_radio_post_requires_authorization(surface,monkeypatch):
    module=load(surface);handler=module.Handler.__new__(module.Handler)
    handler.path='/api/ytr';handler._require_endpoint=Mock(return_value=False)
    gateway=Mock();monkeypatch.setattr(radio_web,'post',gateway)
    handler.do_POST();gateway.assert_not_called()


class Response(io.BytesIO):
    status=206
    headers={'Content-Type':'audio/mp4','Content-Length':'4','Content-Range':'bytes 5-8/100','Accept-Ranges':'bytes'}


def handler(path='/api/ytr/audio?target=paired&id=a&url=http://evil'):
    h=Mock();h.path=path;h.headers={'Range':'bytes=5-8'};h.wfile=io.BytesIO();return h


def test_gateway_preserves_range_and_allowlists_route(monkeypatch):
    h=handler();request=Mock(return_value=Response(b'test'));monkeypatch.setattr(radio_web.urllib.request,'urlopen',request)
    radio_web.handle(h,'http://localhost:7332')
    req=request.call_args.args[0]
    assert req.full_url=='http://localhost:7332/v1/radio/audio?target=paired&id=a'
    assert req.get_header('Range')=='bytes=5-8'
    h.send_response.assert_called_once_with(206)
    h.send_header.assert_any_call('Content-Range','bytes 5-8/100')
    assert h.wfile.getvalue()==b'test'
    with pytest.raises(ValueError):radio_web.handle(handler('/api/ytr/evil'),'http://localhost')


def test_post_rejects_cross_origin_and_non_json():
    h=handler('/api/ytr');h.headers={'Content-Type':'application/json','Origin':'https://evil','Host':'local'}
    with pytest.raises(ValueError,match='Same-origin'):radio_web.post(h,'http://localhost')
    h.headers={'Content-Type':'text/plain'}
    with pytest.raises(ValueError,match='JSON'):radio_web.post(h,'http://localhost')


def test_radio_peer_preserves_partial_audio(monkeypatch):
    h=object.__new__(node.API);h.path='/v1/radio/audio?id=a&target=peer';h.headers={'Range':'bytes=5-8'}
    h._file_target=lambda:({'node':'peer'},'/');h.wfile=io.BytesIO();h.send_response=Mock();h.send_header=Mock();h.end_headers=Mock();h.sendj=Mock()
    monkeypatch.setattr(node,'_copy_route',lambda p:'http://peer')
    monkeypatch.setattr(node.FABRIC_IDENTITY,'auth_headers_for_url',lambda url:{})
    request=Mock(return_value=Response(b'test'));monkeypatch.setattr(node.urllib.request,'urlopen',request)
    h._radio_request()
    assert request.call_args.args[0].get_header('Range')=='bytes=5-8'
    h.send_response.assert_called_once_with(206);h.send_header.assert_any_call('Content-Range','bytes 5-8/100')
    assert h.wfile.getvalue()==b'test'


def test_defaults_follow_cli_owner(tmp_path,monkeypatch):
    monkeypatch.setattr(radio_web.Path,'home',lambda:tmp_path)
    folder=tmp_path/'.config/look';folder.mkdir(parents=True);(folder/'radio.json').write_text(json.dumps({'node':'studio'}))
    response=Response(json.dumps({'peers':[{'node':'studio','trusted':True},{'node':'stranger','trusted':False}]}).encode())
    monkeypatch.setattr(radio_web.urllib.request,'urlopen',lambda *a,**k:response)
    h=handler('/api/ytr/config');radio_web.handle(h,'http://local')
    assert json.loads(h.wfile.getvalue())=={'owner':'studio','owners':['local','studio']}
