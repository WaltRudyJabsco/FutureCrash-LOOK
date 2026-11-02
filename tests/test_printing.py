import base64
from concurrent.futures import ThreadPoolExecutor
import io
import json
from pathlib import Path
import subprocess
import threading
import urllib.request
from unittest.mock import Mock

import pytest
import print_core as core
import printing
from core import node,cognition
from test_media_request_regressions import lk


@pytest.fixture
def spool(tmp_path,monkeypatch):
    monkeypatch.setattr(Path,'home',lambda:tmp_path)
    monkeypatch.setattr(core,'catalog',lambda:{'available':True,'printers':[{'name':'desk'},{'name':'receipt'}]})
    return core.Spool()


def prepare(spool,**kw):return spool.prepare('desk',b'%PDF-1.4\nfixture','novel.pdf',**kw)


def test_draft_does_not_print_and_send_is_single_submission(spool,monkeypatch):
    execute=Mock(return_value='request id is desk-12 (1 file(s))');monkeypatch.setattr(core,'run',execute)
    draft=prepare(spool,options_value={'copies':2,'pages':'1-3,5','media':'Letter','sides':'two-sided-long-edge'})
    assert not execute.called and draft['state']=='prepared'
    assert spool.send(draft['id'])['state']=='prepared' and not execute.called
    receipt=spool.send(draft['id'],confirm=True)
    assert receipt['state']=='queued' and receipt['receipt']['job']=='desk-12'
    assert 'physical' in receipt['receipt']['note']
    assert execute.call_args.args[0]==['lp','-d','desk','-n','2','-t','novel.pdf','-o','page-ranges=1-3,5','-o','media=Letter','-o','sides=two-sided-long-edge','--','-']
    assert execute.call_args.args[1]==b'%PDF-1.4\nfixture'
    spool.send(draft['id'],confirm=True);assert execute.call_count==1
    assert spool.path.stat().st_mode&0o777==0o600


def test_parallel_send_and_timeout_never_duplicate(spool,monkeypatch):
    started=threading.Event();release=threading.Event();calls=[]
    def execute(args,data):
        calls.append(args);started.set();release.wait(2)
        raise subprocess.TimeoutExpired('lp',20)
    monkeypatch.setattr(core,'run',execute);draft=prepare(spool)
    with ThreadPoolExecutor(max_workers=2) as pool:
        one=pool.submit(spool.send,draft['id'],True);assert started.wait(2)
        two=pool.submit(spool.send,draft['id'],True);assert two.result(timeout=2)['state']=='submitting'
        release.set();assert one.result(timeout=2)['state']=='uncertain'
    assert spool.send(draft['id'],True)['state']=='uncertain' and len(calls)==1


def test_changed_profile_expiration_and_discard(spool,monkeypatch):
    draft=prepare(spool)
    monkeypatch.setattr(core,'profiles',lambda:{'desk':{'kind':'escpos','width':384,'columns':32}})
    with pytest.raises(ValueError,match='profile changed'):spool.send(draft['id'],True)
    monkeypatch.setattr(core,'profiles',lambda:{})
    with spool.connect() as db:db.execute('UPDATE jobs SET created=0')
    with pytest.raises(ValueError,match='expired'):spool.send(draft['id'],True)
    assert spool.discard(draft['id'])['state']=='prepared'
    assert spool.discard(draft['id'],True)['state']=='discarded'
    assert spool.get(draft['id'])[3] is None


@pytest.mark.parametrize('options',[{'copies':True},{'copies':21},{'pages':'3-1'},{'pages':'1;echo hi'},{'media':'Letter -o raw'},{'sides':'evil'},{'unknown':'raw'}])
def test_invalid_options_rejected(spool,options):
    with pytest.raises(ValueError):prepare(spool,options_value=options)


def test_receipt_profile_control_codes_and_unicode(spool,monkeypatch):
    with pytest.raises(ValueError,match='profile'):spool.prepare('receipt',b'hello','note.txt','receipt-text')
    core.configure_profile('receipt','escpos',384,32,True)
    draft=spool.prepare('receipt',b'hello','note.txt','receipt-text')
    assert spool.get(draft['id'])[3]==b'\x1b@hello\n\n\n'
    with pytest.raises(ValueError,match='control'):core.receipt_text('hi\x1bp',32)
    with pytest.raises(ValueError,match='unsupported characters'):core.receipt_text('hello 🌞',32)
    with pytest.raises(ValueError,match='PDF'):spool.prepare('receipt',b'%PDF-1.4','x.pdf')
    assert not core.configure_profile('desk','document')['applied']


def test_raster_black_bit_and_white_transparency():
    from PIL import Image
    buffer=io.BytesIO();Image.new('RGBA',(8,1),(0,0,0,255)).save(buffer,format='PNG')
    assert core.receipt_image(buffer.getvalue(),384)==b'\x1dv0\x00\x01\x00\x01\x00\xff\n\n\n'
    buffer=io.BytesIO();Image.new('RGBA',(8,1),(0,0,0,0)).save(buffer,format='PNG')
    assert core.receipt_image(buffer.getvalue(),384)[8:9]==b'\x00'


def test_setup_preview_does_not_mutate_existing_printers(spool,monkeypatch):
    execute=Mock();monkeypatch.setattr(core,'run',execute)
    value=core.add_queue('new_queue','ipps://printer.local/ipp/print')
    assert not value['applied'] and not execute.called
    with pytest.raises(ValueError,match='already exists'):core.add_queue('desk','ipp://printer.local/ipp/print',confirm=True)
    for queue,uri in [('bad;echo','ipp://printer/ipp'),('new','file:///tmp/x'),('new','ipp://user:secret@printer/ipp')]:
        with pytest.raises(ValueError):core.add_queue(queue,uri)
    assert not execute.called
    core.add_queue('new_queue','ipps://printer.local/ipp/print',confirm=True)
    assert execute.call_args.args[0]==['lpadmin','-p','new_queue','-E','-v','ipps://printer.local/ipp/print','-m','everywhere']


def test_queue_discovery_failure_is_useful(monkeypatch):
    monkeypatch.setattr(core,'run',Mock(side_effect=RuntimeError('Missing lpstat')))
    value=core.catalog();assert not value['available'] and not value['printers'] and 'CUPS' in value['setup']


def test_read_only_lo_profile_and_print_route(lk,monkeypatch):
    monkeypatch.setattr(lk,'_cognition_module',lambda:cognition)
    conservative={t['function']['name'] for t in lk._lo_tools('conservative')}
    assert {'printers_list','printer_inspect'}<=conservative and 'print_prepare' not in conservative
    workspace={t['function']['name'] for t in lk._lo_tools('workspace')}
    assert 'print_prepare' in workspace and 'print_send' not in workspace
    route=cognition.analyze('print this document on the receipt printer',use_openjev=False)
    assert route.primary=='printing'


def test_assistant_cannot_upload_files_outside_workspace(tmp_path,monkeypatch):
    monkeypatch.setattr(printing,'request',Mock(side_effect=AssertionError('No upload allowed')))
    with pytest.raises(ValueError,match='inside'):printing.run_tool('print_prepare',{'queue':'desk','path':'../private.txt'},tmp_path)


def test_cli_stages_and_returns_owner_scoped_send_command(tmp_path,monkeypatch,capsys):
    path=tmp_path/'chapter.pdf';path.write_bytes(b'%PDF-1.4 fixture')
    call=Mock(return_value={'id':'a'*32,'state':'prepared','queue':'desk','kind':'document','bytes':16,'options':{'copies':1},'note':'Not sent'});monkeypatch.setattr(printing,'request',call)
    assert printing.main(['file',str(path),'--printer','desk','--node','owner','--pages','1-2'])==0
    args=call.call_args
    assert args.args==('prepare','owner') and args.kwargs['options_value']['pages']=='1-2'
    assert base64.b64decode(args.kwargs['data'])==path.read_bytes()
    assert 'lk print send '+('a'*32)+' --node owner --confirm' in capsys.readouterr().out


def test_http_print_planning_and_explicit_send(spool,monkeypatch):
    monkeypatch.setattr(node,'identity',lambda:{'name':'owner'})
    execute=Mock(return_value='request id is desk-7 (1 file(s))');monkeypatch.setattr(core,'run',execute)
    server=node.FabricHTTPServer(('127.0.0.1',0),node.API,plane='local')
    worker=threading.Thread(target=server.serve_forever,daemon=True);worker.start()
    def request(body=None):
        data=json.dumps(body).encode() if body else None
        with urllib.request.urlopen(urllib.request.Request('http://127.0.0.1:'+str(server.server_port)+'/v1/print',data=data),timeout=3) as response:return json.load(response)
    try:
        assert request()['printers'][0]['name']=='desk'
        plan=request({'action':'prepare','queue':'desk','data':base64.b64encode(b'hello').decode(),'filename':'x.txt'})
        assert not execute.called
        assert request({'action':'send','ident':plan['id']})['state']=='prepared'
        assert request({'action':'send','ident':plan['id'],'confirm':True})['state']=='queued'
        assert request({'action':'send','ident':plan['id'],'confirm':True})['state']=='queued' and execute.call_count==1
    finally:server.shutdown();server.server_close();worker.join(timeout=2)


def test_lo_printer_discovery_is_observed_without_a_model(lk,monkeypatch,capsys):
    from look.lo_engine import EventCollector
    monkeypatch.setattr(printing,'request',lambda *a,**kw:{'printers':[{'name':'desk','node':'owner','status':'idle'}],'errors':[{'node':'offline'}]})
    monkeypatch.setattr(lk,'_save_recent_exchange',Mock())
    monkeypatch.setattr(lk,'_lo_download_direct',Mock(side_effect=AssertionError('No model/download needed')))
    events=EventCollector()
    assert lk.ollama_chat(initial_prompt='What printers are available?',one_shot=True,events=events)==0
    assert 'desk @ owner' in capsys.readouterr().out
    assert any(row.get('edge')=='PRINTERS' for row in events.rows)


def test_remote_print_requires_pairing_and_cannot_forward(spool,monkeypatch):
    api=object.__new__(node.API);api.server=Mock(plane='remote');api.headers={};api.sendj=Mock()
    monkeypatch.setattr(node.FABRIC_IDENTITY,'verify_peer',lambda *a:False)
    assert not api._authorized_ingress('/v1/print')
    assert api.sendj.call_args.args[0]==401
    api.path='/v1/print?target=other'
    with pytest.raises(PermissionError,match='local-control'):api._file_target()


def test_spool_budget_and_invalid_document(spool,monkeypatch):
    monkeypatch.setattr(core,'MAX_PENDING_BYTES',5)
    with pytest.raises(ValueError,match='full'):prepare(spool)
    with pytest.raises(ValueError,match='export'):spool.prepare('desk',b'contents','novel.mercury')
    with pytest.raises(ValueError,match='PDF header'):spool.prepare('desk',b'bad','bad.pdf')


def test_nicknames_resolve_on_owner_preserve_profiles_and_do_not_send(spool,monkeypatch):
    execute=Mock();monkeypatch.setattr(core,'run',execute)
    assert not core.nickname('receipt','Little Printer')['applied']
    core.configure_profile('receipt','escpos',576,48,True)
    core.nickname('receipt','Little Printer',True)
    assert core.require_queue('little printer')=='receipt'
    assert core.profiles()['receipt']['width']==576
    plan=spool.prepare('Little Printer',b'To do\n- Buy paper','note.txt','receipt-text')
    assert plan['queue']=='receipt' and plan['text_preview']=='To do\n- Buy paper'
    with pytest.raises(ValueError,match='already belongs'):core.nickname('desk','Little Printer',True)
    assert not execute.called
    assert 'text_preview' not in spool.discard(plan['id'],True)


def test_notes_to_receipt_tool_chain_uses_observed_text(spool,monkeypatch,tmp_path):
    import notebook
    core.configure_profile('receipt','escpos',384,32,True);core.nickname('receipt','Little Printer',True)
    # This store read supplies the same full body that LO receives from Notes.
    store=Mock();store.list.return_value=[{'id':'todo','title':'Today','body':'- Buy paper\n- Call the library','kind':'task'}]
    monkeypatch.setattr(notebook,'Notebook',lambda:store)
    notes=json.loads(notebook.tool('notebook_list',{}))
    monkeypatch.setattr(printing,'request',lambda action,node='local',**fields:dict(core.local(dict(action=action,**fields)),node='owner'))
    result=json.loads(printing.run_tool('print_prepare',{'queue':'Little Printer','text':notes[0]['body'],'receipt':True},tmp_path))
    assert result['state']=='prepared' and result['text_preview']==notes[0]['body']
    assert result['queue']=='receipt'
    route=cognition.analyze('print this todo list from notes on the little printer',use_openjev=False)
    assert {'notebook_read','notebook_list','notebook_search','print_prepare'}<=set(route.allowed_tools)


def test_read_only_inspection_cannot_smuggle_mutation(monkeypatch,tmp_path):
    monkeypatch.setattr(printing,'request',Mock(side_effect=AssertionError('No mutation allowed')))
    with pytest.raises(ValueError,match='read-only'):printing.run_tool('printer_inspect',{'queue':'desk','view':'send'},tmp_path)
    with pytest.raises(ValueError,match='accepts only'):printing.run_tool('printer_inspect',{'queue':'desk','view':'options','confirm':True},tmp_path)


def test_unverified_job_id_never_claims_queued(spool,monkeypatch):
    execute=Mock(return_value='connection closed without job receipt');monkeypatch.setattr(core,'run',execute)
    draft=spool.prepare('desk',b'private todo','todo.txt')
    result=spool.send(draft['id'],True)
    assert result['state']=='uncertain' and result['receipt']['job'] is None
    assert 'text_preview' not in result and spool.get(draft['id'])[3] is None
    assert spool.send(draft['id'],True)['state']=='uncertain' and execute.call_count==1
