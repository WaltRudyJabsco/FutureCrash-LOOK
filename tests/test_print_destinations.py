import json
from unittest.mock import Mock
import pytest
import print_destinations as physical
import printing
import print_core

U1='11111111-1111-1111-1111-111111111111'
U2='22222222-2222-2222-2222-222222222222'


def row(queue,node='mac',uuid=U1,status='is idle'):
    return {'name':queue,'node':node,'status':status,'profile':{'kind':'document'},'device':{'keys':['uuid:'+uuid],'label':'Photo Printer'}}


def test_same_printer_routes_consolidate_but_same_model_different_uuid_stays_distinct():
    rows=[row('photo'),row('photo_2'),row('photo','tower'),row('photo','other',U2)]
    groups=physical.consolidate(rows)
    assert len(groups)==2 and sorted(g['route_count'] for g in groups)==[1,3]
    assert physical.consolidate(list(reversed(rows)))==groups
    with pytest.raises(ValueError,match='several'):physical.choose({'printers':groups},'Photo Printer')


def test_bonjour_and_ipps_endpoints_share_observed_uuid():
    observed=[{'uri':'ipp://photo.local:631/ipp/print','uuid':U1,'label':'Photo Printer'}]
    a=physical.device('dnssd://Photo%20Printer._ipps._tcp.local./?uuid='+U1,observed)
    b=physical.device('ipps://photo.local.:631/ipp/print',observed)
    assert 'uuid:'+U1 in set(a['keys'])&set(b['keys'])
    assert physical.endpoint('ipp://server/printers/A')!=physical.endpoint('ipp://server/printers/B')
    assert physical.endpoint('file:///private/file')==''


def test_unknown_identity_never_merges_by_queue_name():
    groups=physical.consolidate([{'name':'same_model','node':'one'},{'name':'same_model','node':'two'}])
    assert len(groups)==2 and not any(g['identity_verified'] for g in groups)


def test_no_bridge_between_conflicting_device_uuids():
    a=row('one');b=row('two',uuid=U2)
    for item in [a,b]:item['device']['keys'].append('service:photo')
    unknown={'name':'unknown','node':'mac','device':{'keys':['service:photo']}}
    groups=physical.consolidate([a,b,unknown])
    assert len(groups)==3


def test_choose_enabled_route_before_dispatch_and_never_retry_write(monkeypatch):
    groups=physical.consolidate([row('photo','mac',status='disabled'),row('photo','tower')])
    def request(action,node,**fields):
        if action=='list':return {'printers':groups,'local_node':'mac'}
        assert node=='tower' and fields['queue']=='photo'
        raise RuntimeError('unknown delivery')
    execute=Mock(side_effect=request);monkeypatch.setattr(printing,'_request',execute)
    with pytest.raises(RuntimeError,match='unknown'):printing.request('prepare','auto',queue='Photo Printer',data='bytes')
    assert execute.call_count==2 # catalog + precisely one prepare dispatch


def test_auto_prepare_returns_pinned_owner_command(monkeypatch):
    groups=physical.consolidate([row('photo','tower')])
    def request(action,node,**fields):
        if action=='list':return {'printers':groups,'local_node':'mac'}
        return {'id':'a'*32,'node':'tower','queue':fields['queue'],'state':'prepared'}
    monkeypatch.setattr(printing,'_request',request)
    result=printing.prepare('Photo Printer',text='hello')
    assert '--node tower --confirm' in result['send_command'] and '--node auto' not in result['send_command']


def test_nickname_updates_routes_but_does_not_hide_partial_failures(monkeypatch):
    groups=physical.consolidate([row('photo','mac'),row('photo','tower')])
    def request(action,node,**fields):
        if action=='list':return {'printers':groups}
        if node=='tower':raise RuntimeError('offline')
        return {'applied':True,'node':node}
    monkeypatch.setattr(printing,'_request',request)
    result=printing.request('nickname','auto',queue=groups[0]['id'],label='Epson',confirm=True)
    assert len(result['routes'])==2 and any(value.get('error') for value in result['routes'])


def test_live_completion_file_and_optional_printer_parser():
    from pathlib import Path
    assert printing.parser().parse_args(['options']).queue is None
    assert printing.parser().parse_args(['file','chapter.pdf']).printer is None
    completion=(Path(__file__).resolve().parents[1]/'look/completions/_lk').read_text()
    assert 'lk print list --json' in completion and 'options|jobs|nickname|profile' in completion


def test_same_physical_local_queues_can_share_nickname(tmp_path,monkeypatch):
    from pathlib import Path
    monkeypatch.setattr(Path,'home',lambda:tmp_path)
    rows=[row('photo'),row('photo_2')]
    monkeypatch.setattr(print_core,'catalog',lambda:{'printers':rows})
    print_core.nickname('photo','Epson',True);print_core.nickname('photo_2','Epson',True)
    assert print_core.require_queue('Epson')=='photo'


def test_zsh_completion_returns_names_with_spaces(tmp_path):
    import subprocess
    from pathlib import Path
    source=Path(__file__).resolve().parents[1]/'look/completions/_lk'
    script='''
source "$1"
lk() { print -r -- '{"printers":[{"label":"Brother MFC"},{"label":"Epson Photo"}]}'; }
_describe() { print -rl -- "${printers[@]}"; }
CURRENT=4
words=(lk print options '')
_lk
'''
    result=subprocess.run(['zsh','-f','-c',script,'completion-test',str(source)],capture_output=True,text=True,check=True)
    assert result.stdout.splitlines()==['Brother MFC','Epson Photo']
