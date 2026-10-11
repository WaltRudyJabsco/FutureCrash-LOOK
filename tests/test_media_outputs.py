import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock
import pytest
from look import media_outputs as m


def test_native_outputs_prefer_host_backend_and_clean_labels(monkeypatch):
 monkeypatch.setattr(m.sys,'platform','darwin')
 rows=m.audio_devices("  'auto' (Autoselect)\n 'coreaudio/UID' (Speaker\x1b)\n 'avfoundation/UID' (Speaker)")
 assert len(rows)==1 and rows[0]['label']=='Speaker' and rows[0]['available']


def test_raop_identity_survives_dhcp_address_and_backend_changes(monkeypatch):
 monkeypatch.setattr(m.sys,'platform','linux')
 a=m.audio_devices(" 'pipewire/raop_sink.Bose-123.local.192.168.1.3.7000' (Office)\n 'pulse/raop_sink.Bose-123.local.192.168.1.3.7000' (Office)")
 b=m.audio_devices(" 'pulse/raop_sink.Bose-123.local.192.168.1.4.7000' (Office)")
 assert len(a)==1 and a[0]['kind']=='airplay' and a[0]['output_id']==b[0]['output_id']


def test_selection_is_current_user_only_and_never_uses_stale_device(tmp_path,monkeypatch):
 monkeypatch.setattr(m,'config_path',lambda:tmp_path/'output.json')
 row={'output_id':'audio-a','device':'pipewire/speaker','label':'Office'}
 monkeypatch.setattr(m,'native',lambda:[row])
 m.select('audio-a');assert m.selected_device()=='pipewire/speaker'
 assert (tmp_path/'output.json').stat().st_mode&0o777==0o600
 monkeypatch.setattr(m,'native',lambda:[])
 with pytest.raises(ValueError,match='disconnected'):m.selected_device()
 rows=m.catalog();assert rows[0]['selected'] and not rows[0]['available']
 m.select('default');assert m.selected_device()=='auto'


def test_failed_player_change_does_not_save_selection(tmp_path,monkeypatch):
 monkeypatch.setattr(m,'config_path',lambda:tmp_path/'output.json')
 monkeypatch.setattr(m,'native',lambda:[{'output_id':'a','device':'x','label':'Speaker'}])
 with pytest.raises(ValueError,match='rejected'):m.select('a',lambda cmd:{'error':'failure'})
 assert not (tmp_path/'output.json').exists()


def test_unconfirmed_change_rolls_back(monkeypatch):
 monkeypatch.setattr(m,'native',lambda:[{'output_id':'a','device':'x','label':'Speaker'}])
 monkeypatch.setattr(m,'read',lambda:{'device':'previous'})
 request=Mock(side_effect=[{'error':'success'},{'data':'wrong'},{'error':'success'}])
 with pytest.raises(ValueError,match='confirm'):m.select('a',request)
 assert request.call_args.args[0]==['set_property','audio-device','previous']


def test_airplay_enable_preserves_system_default(monkeypatch):
 monkeypatch.setattr(m.sys,'platform','linux')
 calls=[]
 responses=iter(['original','','42','new',''])
 def run(argv,**kw):
  calls.append(argv);return SimpleNamespace(returncode=0,stdout=next(responses),stderr='')
 monkeypatch.setattr(m.subprocess,'run',run)
 monkeypatch.setattr(m.shutil,'which',lambda name:'/usr/bin/pactl')
 assert m.enable_airplay()['ok']
 assert calls[-1][-2:]==['set-default-sink','original']
 assert any('module-raop-discover' in c for c in calls)


def test_airplay_mac_discovery_is_bounded_and_not_playable(monkeypatch):
 monkeypatch.setattr(m.sys,'platform','darwin');monkeypatch.setattr(m.shutil,'which',lambda name:'/usr/bin/dns-sd')
 out='10:00 Add 2 14 local. _raop._tcp. ABC@Office AirPort Express\n10:00 Add 2 14 local. _raop._tcp. ABC@Office AirPort Express'
 process=Mock();process.communicate.return_value=(out,'');process.poll.return_value=0
 monkeypatch.setattr(m.subprocess,'Popen',lambda *args,**kw:process)
 rows=m.airplay();assert len(rows)==1 and not rows[0]['available']
 process.communicate.assert_called_once_with(timeout=m.DISCOVERY_SECONDS)


def test_discovery_never_changes_config(tmp_path,monkeypatch):
 monkeypatch.setattr(m,'config_path',lambda:tmp_path/'output.json')
 monkeypatch.setattr(m,'native',lambda:[]);monkeypatch.setattr(m,'airplay',lambda:[])
 assert m.catalog(True)==[];assert not (tmp_path/'output.json').exists()


def test_unreachable_receiver_is_visible_but_cannot_be_selected(tmp_path,monkeypatch):
 monkeypatch.setattr(m,'config_path',lambda:tmp_path/'output.json')
 row={'output_id':'a','label':'Airport','device':'pipewire/raop_sink.Office.local.169.254.1.1.7000','kind':'airplay','available':True}
 monkeypatch.setattr(m,'native',lambda:[row.copy()]);monkeypatch.setattr(m.socket,'create_connection',Mock(side_effect=OSError('unreachable')))
 assert not m.catalog()[0]['available']
 with pytest.raises(ValueError,match='unreachable'):m.select('a')
 assert not (tmp_path/'output.json').exists()


def test_node_advertises_native_outputs_without_breaking_default(monkeypatch):
 from core import node
 monkeypatch.setattr(node,'_local_media_state',lambda:{'state':'paused','active':True})
 monkeypatch.setattr(node,'_media_player_binary',lambda:'/bin/mpv');monkeypatch.setattr(node,'_look_command',lambda:'/bin/lk')
 monkeypatch.setattr(node,'identity',lambda:{'name':'bridge'})
 monkeypatch.setattr(node.subprocess,'run',lambda *args,**kw:SimpleNamespace(returncode=0,stdout=json.dumps({'outputs':[{'output_id':'audio-a','label':'Office','available':True,'selected':True}]})))
 result=node._local_media_output()
 assert result['output_id']=='default' and result['available']
 assert result['outputs'][1]['node']=='bridge' and result['outputs'][1]['label']=='Office'
 assert not result['outputs'][0]['selected']


def test_output_route_uses_local_chooser_and_returns_structured_result(monkeypatch):
 from core import node
 monkeypatch.setattr(node,'_look_command',lambda:'/bin/lk');monkeypatch.setattr(node,'identity',lambda:{'name':'bridge'})
 run=Mock(return_value=SimpleNamespace(returncode=0,stdout='{"ok":true,"message":"Selected Office"}'))
 monkeypatch.setattr(node.subprocess,'run',run)
 assert node._local_media_route('output',{'output_id':'audio-a'})['node']=='bridge'
 assert run.call_args.args[0]==['/bin/lk','media','output-local','select','audio-a']


def test_incomplete_peer_discovery_does_not_drop_local_outputs(monkeypatch):
 from core import node
 local={'output_id':'default','node':'local','available':True}
 monkeypatch.setattr(node,'_local_media_output',lambda *args:{'outputs':[local]})
 monkeypatch.setattr(node,'node_info',lambda:{})
 monkeypatch.setattr(node.PEERS,'public',lambda:[{'name':'offline','trusted':True}])
 monkeypatch.setattr(node,'_peer_json',Mock(side_effect=TimeoutError('sleeping')))
 result=node._fabric_media_outputs()
 assert result['outputs']==[local] and result['errors'][0]['node']=='offline'


def test_queue_move_keeps_web_urls_and_streams_owner_local_files(monkeypatch):
 from core import node
 monkeypatch.setattr(node,'identity',lambda:{'name':'source'})
 monkeypatch.setattr(node,'_fabric_media_full_session',lambda source:{'queue':[{'path':'https://archive.org/download/item/video.mp4'},{'path':'/music/song.flac'}]})
 monkeypatch.setattr(node,'node_info',lambda:{})
 monkeypatch.setattr(node.PEERS,'public',lambda:[])
 monkeypatch.setattr(node,'_remote_url',lambda snapshot,name,path:'https://source'+path)
 route=Mock(return_value={'ok':True});monkeypatch.setattr(node,'_fabric_media_route',route)
 result=node._fabric_media_move('source','bridge')
 queue=route.call_args_list[0].args[2]['session']['queue']
 assert queue[0]['path']=='https://archive.org/download/item/video.mp4'
 assert queue[1]['path']=='https://source/v1/media/audio?index=1'
 assert route.call_args_list[1].args==('source','control',{'action':'stop'})
 assert result['moved_to']=='bridge'


def launch_function(monkeypatch):
 import ast,sys
 source=(Path(__file__).resolve().parents[1]/'look/lk').read_text()
 tree=ast.parse(source)
 function=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='_media_launch_session')
 namespace={'subprocess':m.subprocess,'media_core':SimpleNamespace(normalize_session=lambda value:value),
 '_media_pin_playable_rows':lambda rows:(rows,[]),'_media_mpv_binary':lambda:'/bin/mpv',
 '_media_write_m3u':lambda rows:(rows,[],[0]),'_media_queue_has_video':lambda rows:False,
 '_media_mpv_alive':lambda:True,'_media_reuse_needs_visible_restart':lambda video:False,
 'MEDIA_QUEUE_FILE':Path('/tmp/queue.m3u8')}
 monkeypatch.setitem(sys.modules,'media_outputs',m)
 exec(compile(ast.Module(body=[function],type_ignores=[]),'<launch-test>','exec'),namespace)
 return namespace


def test_missing_selected_device_fails_before_queue_mutation(monkeypatch):
 ns=launch_function(monkeypatch)
 pin=Mock();ns['_media_pin_playable_rows']=pin
 monkeypatch.setattr(m,'selected_device',Mock(side_effect=ValueError('disconnected')))
 assert ns['_media_launch_session']({'queue':[{'path':'a'}]})==1
 pin.assert_not_called()


def test_player_rejects_output_before_loading_replacement_queue(monkeypatch):
 ns=launch_function(monkeypatch)
 request=Mock(return_value={'error':'failure'});ns['_media_mpv_request']=request
 monkeypatch.setattr(m,'selected_device',lambda:'pipewire/speaker')
 assert ns['_media_launch_session']({'queue':[{'path':'a'}]})==1
 request.assert_called_once_with(['set_property','audio-device','pipewire/speaker'])


def test_remote_outputs_use_trusted_peer_name(monkeypatch):
 from core import node
 monkeypatch.setattr(node,'_local_media_output',lambda *args:{'outputs':[]})
 monkeypatch.setattr(node,'node_info',lambda:{})
 monkeypatch.setattr(node.PEERS,'public',lambda:[{'name':'bridge','trusted':True}])
 monkeypatch.setattr(node,'_peer_json',lambda *args,**kw:{'outputs':[{'node':'wrong','output_id':'default'}]})
 assert node._fabric_media_outputs()['outputs'][-1]['node']=='bridge'


@pytest.mark.parametrize('command,extra,operation',[
 ('media-output',['audio-a'],'output'),('media-airplay',[],'airplay'),('media-move',[],'move')])
def test_output_commands_reach_daemon_with_supported_timeout(monkeypatch,capsys,command,extra,operation):
 from core import node
 import sys
 request=Mock(return_value={'ok':True,'message':'confirmed'})
 monkeypatch.setattr(node,'http_json',request)
 monkeypatch.setattr(sys,'argv',['fcl-node',command,*extra,'--node','bridge','--json'])
 assert node.main()==0
 assert request.call_args.kwargs['timeout']==90
 body=request.call_args.args[1]
 assert body['operation']==operation and body['node']=='bridge'
 assert json.loads(capsys.readouterr().out)['ok']
