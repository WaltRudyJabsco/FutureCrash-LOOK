"""Museum print routing tests: never touch a printer or the network."""
import io
import json
import urllib.error
from urllib.parse import urlsplit,parse_qs
import pytest
from core import museum_web

@pytest.fixture
def gateway(monkeypatch):
    calls=[]
    catalog={'local_node':'desk','printers':[
        {'id':'office','label':'Office','routes':[{'node':'desk','name':'office','profile':{},'status':'idle'}]},
        {'id':'receipt','label':'Little Printer','routes':[{'node':'archive','name':'tiny','profile':{'kind':'escpos'},'status':'idle'}]}]}
    def open_url(req,**kwargs):
        url=req if isinstance(req,str) else req.full_url
        data=None if isinstance(req,str) or req.data is None else json.loads(req.data)
        calls.append((url,data))
        if url.endswith('/fabric'):value=catalog
        elif '/museum/image?' in url:return io.BytesIO(b'example image')
        elif data['action']=='prepare':value={'id':'a'*32,'node':parse_qs(urlsplit(url).query)['target'][0],'estimated_paper_mm':61}
        else:value={'state':'queued' if data['action']=='send' else 'discarded'}
        return io.BytesIO(json.dumps(value).encode())
    monkeypatch.setattr(museum_web.urllib.request,'urlopen',open_url)
    return calls,catalog

def test_list_prefers_receipt_without_preparing(gateway):
    calls,_=gateway
    assert museum_web.print_request('http://local')['printers'][0]['id']=='receipt'
    assert len(calls)==1

@pytest.mark.parametrize('printer,kind,node',[('receipt','receipt-image','archive'),('office','document','desk')])
def test_prepare_uses_exact_artwork_and_destination_without_sending(gateway,printer,kind,node):
    calls,_=gateway
    plan=museum_web.print_request('http://local',{'action':'prepare','target':'library','id':'aic-89503','printer':printer})
    assert plan['node']==node
    assert parse_qs(urlsplit(calls[1][0]).query)=={'target':['library'],'id':['aic-89503']}
    assert calls[2][1]['kind']==kind and calls[2][1]['options_value']=={'copies':1}
    assert not any(data and data['action']=='send' for _,data in calls)

@pytest.mark.parametrize('payload',[
 {'action':'prepare','id':'https://example.com/image','printer':'receipt'},
 {'action':'prepare','id':'aic-1','printer':'not discovered'},
 {'action':'send','id':'a'*32,'node':'archive'},
 {'action':'send','id':'oops','confirm':True},
 {'action':'send','id':'a'*32,'confirm':True,'path':'/tmp/file'},
])
def test_invalid_print_requests_cannot_submit(gateway,payload):
    with pytest.raises(ValueError):museum_web.print_request('http://local',payload)
    assert not any(data and data['action']=='send' for _,data in gateway[0])

def test_send_keeps_prepared_owner(gateway):
    museum_web.print_request('http://local',{'action':'send','node':'archive','id':'a'*32,'confirm':True})
    assert gateway[0]==[('http://local/v1/print?target=archive',{'action':'send','ident':'a'*32,'confirm':True})]

def test_paper_limit_error_survives_gateway(monkeypatch):
    def fail(*args,**kwargs):raise urllib.error.HTTPError('http://local',400,'Bad request',{},io.BytesIO(b'{"error":"Receipt exceeds 25 cm"}'))
    monkeypatch.setattr(museum_web.urllib.request,'urlopen',fail)
    with pytest.raises(ValueError,match='25 cm'):museum_web.print_request('http://local')
