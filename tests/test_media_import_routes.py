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
