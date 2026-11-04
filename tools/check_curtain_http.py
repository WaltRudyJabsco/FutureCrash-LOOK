"""Run with the service interpreter; isolated HTTP PIN lifecycle smoke test."""
import json,sys,tempfile,threading,urllib.request
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'core'))
import node,curtain
from http.server import ThreadingHTTPServer
with tempfile.TemporaryDirectory() as folder:
    curtain.path=lambda:Path(folder)/'state.json';curtain.desktop=lambda:'test only'
    node._curtain_request=lambda data:curtain.operate(data,'test',[],lambda *_:None)
    server=node.FabricHTTPServer(('127.0.0.1',0),node.API)
    thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    try:
        for action in ('setup','lock','unlock'):
            body=json.dumps({'action':action,'pin':'1234'}).encode()
            with urllib.request.urlopen(urllib.request.Request('http://127.0.0.1:%s/v1/curtain'%server.server_port,data=body,headers={'Content-Type':'application/json'})) as response:
                result=json.load(response);assert result['ok']
        print('Service Python HTTP setup/lock/unlock passed; isolated temporary state')
    finally:server.shutdown();server.server_close()
