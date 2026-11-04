import ast,io,json
from pathlib import Path
from types import SimpleNamespace
from urllib.parse import urlparse
import pytest
ROOT=Path(__file__).resolve().parents[1]

@pytest.mark.parametrize('surface,call,reply',[('albert','node_json','send_json'),('signal-window','_node_call','json')])
@pytest.mark.parametrize('payload,authorized,origin,expected',[
    ({'action':'lock'},True,'http://test',200),
    ({'action':'unlock','pin':'1234'},True,'http://test',200),
    ({'action':'setup','pin':'1234'},True,'http://test',400),
    ({'action':'receive','event':{}},True,'http://test',400),
    ({'action':'lock'},True,'http://evil',400),
    ({'action':'lock'},False,'http://test',None),
])
def test_web_boundary(surface,call,reply,payload,authorized,origin,expected):
    tree=ast.parse((ROOT/surface/'server.py').read_text())
    method=next(n for n in ast.walk(tree) if isinstance(n,ast.FunctionDef) and n.name=='do_POST')
    namespace={'urlparse':urlparse,'json':json};sent=[];responses=[]
    namespace[call]=lambda path,data,**_:sent.append(data) or {'ok':True,'locked':data['action']=='lock'}
    exec(compile(ast.Module(body=[method],type_ignores=[]),'<handler>','exec'),namespace)
    data=json.dumps(payload).encode()
    handler=SimpleNamespace(path='/api/curtain',headers={'Content-Type':'application/json','Content-Length':str(len(data)),'Origin':origin,'Host':'test'},rfile=io.BytesIO(data),_require_endpoint=lambda _:authorized)
    setattr(handler,reply,lambda code,body:responses.append((code,body)))
    namespace['do_POST'](handler)
    assert (responses[0][0] if responses else None)==expected
    assert bool(sent)==(expected==200)
    assert '1234' not in str(responses)
