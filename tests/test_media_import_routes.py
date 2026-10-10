import json
import sys
from unittest.mock import Mock
from core import node
from look import disc_import


def api(monkeypatch,payload):
    monkeypatch.setitem(sys.modules,'disc_import',disc_import)
    monkeypatch.setattr(node,'_look_catalog_modules',lambda:None)
    monkeypatch.setattr(node,'identity',lambda:{'name':'3090'})
    value=node.API.__new__(node.API);value.path='/v1/media/import'
    value._authorized_ingress=lambda path:True;value.body=lambda:payload;value.sendj=Mock()
    return value


def test_api_reports_owner_and_validates_request_shape(monkeypatch):
    dispatch=Mock(return_value={'ok':True,'job':{'id':'job'}});monkeypatch.setattr(disc_import,'request',dispatch)
    value=api(monkeypatch,{'action':'start','payload':{'kind':'cd'}});value.do_POST()
    dispatch.assert_called_once_with('start',{'kind':'cd'})
    assert value.sendj.call_args.args[1]['node']=='3090'
    value=api(monkeypatch,{'action':'start','payload':'invalid'});value.do_POST()
    assert value.sendj.call_args.args[0]==400


def test_ingress_authorization_precedes_import_effects(monkeypatch):
    dispatch=Mock();monkeypatch.setattr(disc_import,'request',dispatch)
    value=api(monkeypatch,{'action':'start','payload':{}});value._authorized_ingress=lambda path:False
    value.do_POST();dispatch.assert_not_called()


def test_cli_routes_to_named_owner_with_structured_payload(monkeypatch,capsys):
    routed=Mock(return_value={'ok':True,'node':'3090','drives':[]});monkeypatch.setattr(node,'_target_post',routed)
    monkeypatch.setattr(sys,'argv',['fcl-node','disc-import','drives','{}','--node','3090','--json'])
    assert node.main()==0
    assert routed.call_args.args[2:]==('3090','/v1/media/import',{'action':'drives','payload':{}})
    assert json.loads(capsys.readouterr().out)['node']=='3090'


def test_mutation_discovers_live_route_and_sends_only_once(monkeypatch):
    peer={'name':'3090','trusted':True,'node_id':'paired-id','url':'https://stale'}
    monkeypatch.setattr(node,'_daemon_get',lambda *args:{'self':{'name':'Mac'},'peers':[peer]})
    monkeypatch.setattr(node,'_file_race',lambda *args:('https://live',{'node_id':'paired-id'}))
    sent=Mock(return_value={'ok':True});monkeypatch.setattr(node,'http_json',sent)
    node._target_post('127.0.0.1',7332,'3090','/v1/media/import',{'action':'start'})
    assert sent.call_count==1 and sent.call_args.args[0]=='https://live/v1/media/import'


def test_mutation_rejects_wrong_identity_before_effect(monkeypatch):
    import pytest
    peer={'name':'3090','trusted':True,'node_id':'paired-id'}
    monkeypatch.setattr(node,'_daemon_get',lambda *args:{'self':{'name':'Mac'},'peers':[peer]})
    monkeypatch.setattr(node,'_file_race',lambda *args:('https://wrong',{'node_id':'other-id'}))
    sent=Mock();monkeypatch.setattr(node,'http_json',sent)
    with pytest.raises(PermissionError):node._target_post('127.0.0.1',7332,'3090','/v1/media/import',{})
    sent.assert_not_called()
