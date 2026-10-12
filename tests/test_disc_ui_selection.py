import io
import time
from unittest.mock import Mock

import pytest
from look import disc_ui, media_storage


def job(number,title='Album',state='complete',delivery=None):
    row={'id':f'{number:032x}','title':title,'kind':'cd','state':state,'stage':state,'created':time.time(),'metadata':{'artist':'Band'}}
    if delivery:row['delivery']={'state':delivery}
    return row


@pytest.fixture
def plain(monkeypatch):
    monkeypatch.setattr(disc_ui.sys,'stdin',io.StringIO())


def test_deliver_uses_remembered_destination_and_single_undelivered_album(plain,monkeypatch,capsys):
    monkeypatch.setattr(media_storage,'settings',lambda:{'node':'3090','root':'/media/Library'})
    request=Mock(side_effect=[{'jobs':[job(1,delivery='complete'),job(2,'New Album')]},{'ok':True}])
    assert disc_ui.main(['deliver'],lambda node:request,None,None)==0
    assert request.call_args.args==('deliver',{'drive':None,'kind':'cd','id':f'{2:032x}','destination':'@3090:/media/Library'})
    output=capsys.readouterr().out
    assert '3090' in output and f'{2:032x}' not in output and '/media/Library' not in output


def test_multiple_deliveries_require_choice_before_mutating(plain,capsys):
    request=Mock(return_value={'jobs':[job(1,'First'),job(2,'Second')]})
    assert disc_ui.main(['deliver'],lambda node:request,None,None)==1
    assert request.call_count==1
    assert 'First' in capsys.readouterr().err


@pytest.mark.parametrize('selector,expected',[('second',2),('Band',None),('latest',1),('00000000000000000000000000000002',2)])
def test_job_names_latest_and_full_ids(plain,selector,expected):
    request=Mock(return_value={'jobs':[job(1,'First'),job(2,'Second')]})
    if expected is None:
        with pytest.raises(ValueError,match='More than one'):disc_ui.resolve_job(request,selector,'deliver')
    else:assert disc_ui.resolve_job(request,selector,'deliver')==f'{expected:032x}'


def test_multiword_album_selector_and_retry(plain,monkeypatch):
    request=Mock(side_effect=[{'jobs':[job(2,'New Album',delivery='failed')]},{'ok':True}])
    assert disc_ui.main(['deliver','New','Album','--destination','@3090:/media'],lambda node:request,None,None)==0
    assert request.call_args.args[1]['id']==f'{2:032x}'


def test_watch_without_id_reports_all_active_work(plain,capsys):
    request=Mock(return_value={'jobs':[job(1,'Rip',state='running'),job(2,'Transfer',delivery='running'),job(3,'Old')]})
    assert disc_ui.main(['watch'],lambda node:request,None,None)==0
    output=capsys.readouterr().out
    assert 'Rip' in output and 'Transfer' in output and 'Old' not in output


def test_default_watch_uses_fabric_and_explicit_node_stays_scoped(plain):
    factory=Mock(return_value=Mock(return_value={'jobs':[]}))
    assert disc_ui.main(['watch'],factory,None,None)==0
    factory.assert_called_with('fabric')
    assert disc_ui.main(['watch','--node','local'],factory,None,None)==0
    factory.assert_called_with('local')


def test_fabric_watch_labels_owners_and_unavailable_nodes(plain,capsys):
    first=dict(job(1,'Remote film','running'),node='Tower')
    request=Mock(return_value={'fabric':True,'jobs':[first,job(2,'Old')],'unavailable':[{'node':'Sleeping laptop'}]})
    assert disc_ui.main(['watch'],lambda node:request,None,None)==0
    output=capsys.readouterr().out
    assert 'Tower · Remote film' in output and 'Sleeping laptop' in output and 'Old' not in output


def test_fabric_jobs_collect_trusted_owners_and_isolate_failures(monkeypatch):
    from core import node
    peers=[{'name':'Tower','trusted':True},{'name':'Tower','trusted':True},
           {'name':'Sleeping','trusted':True},{'name':'Stranger','trusted':False}]
    monkeypatch.setattr(node,'_daemon_get',lambda host,port,path:{'self':{'name':'Laptop'},'peers':peers} if path=='/v1/nodes' else {'jobs':[job(1)]})
    calls=[]
    def remote(peer,path):
        calls.append(peer['name'])
        if peer['name']=='Sleeping':raise TimeoutError('offline')
        return {'jobs':[job(2,'Remote film','running')]}
    monkeypatch.setattr(node,'_file_peer_json',remote)
    result=node._fabric_import_jobs('localhost',7332)
    assert sorted(calls)==['Sleeping','Tower']
    assert {row['node'] for row in result['jobs']}=={'Laptop','Tower'}
    assert result['unavailable']==[{'node':'Sleeping','error':'offline'}]


def test_watch_without_active_work_shows_latest_result(plain,capsys):
    request=Mock(return_value={'jobs':[job(1,'Latest Album'),job(2,'Older Album')]})
    assert disc_ui.main(['watch'],lambda node:request,None,None)==0
    assert 'Latest Album' in capsys.readouterr().out


def test_cancel_needs_explicit_selection(plain,capsys):
    request=Mock()
    assert disc_ui.main(['cancel'],lambda node:request,None,None)==1
    request.assert_not_called()
    assert 'requires an album name' in capsys.readouterr().err


def test_interactive_album_picker_returns_chosen_album(monkeypatch):
    monkeypatch.setattr(disc_ui.sys.stdin,'isatty',lambda:True)
    monkeypatch.setattr(disc_ui.sys.stdout,'isatty',lambda:True)
    monkeypatch.setattr('builtins.input',lambda prompt:'2')
    request=Mock(return_value={'jobs':[job(1,'First'),job(2,'Second')]})
    assert disc_ui.resolve_job(request,'','deliver')==f'{2:032x}'


def test_interactive_watch_renders_all_active_work_and_restores_terminal(monkeypatch):
    class Terminal(io.StringIO):
        def fileno(self):return 0
    incoming=Terminal();outgoing=Terminal()
    monkeypatch.setattr(disc_ui.sys,'stdin',incoming)
    monkeypatch.setattr(disc_ui.sys,'stdout',outgoing)
    monkeypatch.setattr(disc_ui.termios,'tcgetattr',lambda fd:['saved'])
    restore=Mock();monkeypatch.setattr(disc_ui.termios,'tcsetattr',restore)
    monkeypatch.setattr(disc_ui.tty,'setcbreak',lambda fd:None)
    request=Mock(return_value={'jobs':[job(1,'Ripping',state='running'),job(2,'Delivering',delivery='running')]})
    assert disc_ui.watch_all(request,lambda fd,timeout:'esc',lambda text,width:text)==0
    assert 'Ripping' in outgoing.getvalue() and 'Delivering' in outgoing.getvalue()
    restore.assert_called_once_with(0,disc_ui.termios.TCSADRAIN,['saved'])


def test_idle_fabric_monitor_sees_reconnecting_work(monkeypatch):
    class Terminal(io.StringIO):
        def fileno(self):return 0
    monkeypatch.setattr(disc_ui.sys,'stdin',Terminal())
    output=Terminal();monkeypatch.setattr(disc_ui.sys,'stdout',output)
    monkeypatch.setattr(disc_ui.termios,'tcgetattr',lambda fd:['saved'])
    monkeypatch.setattr(disc_ui.termios,'tcsetattr',lambda *args:None)
    monkeypatch.setattr(disc_ui.tty,'setcbreak',lambda fd:None)
    request=Mock(side_effect=[{'fabric':True,'jobs':[]},
                             {'fabric':True,'jobs':[dict(job(1,'Reconnected film','running'),node='Tower')]}])
    keys=iter([None,'esc'])
    assert disc_ui.watch_all(request,lambda *args:next(keys),lambda text,width:text)==0
    assert request.call_count==2 and 'Tower · Reconnected film' in output.getvalue()
