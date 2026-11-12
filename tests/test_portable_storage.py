"""Portable registration without changing backup ownership or trusting unknown disks."""
import copy
import json
import shutil
import time
from pathlib import Path
import pytest
from core import portable_storage as s

@pytest.fixture
def setup(tmp_path):
    home=tmp_path/'account'; drive=tmp_path/'drive'; drive.mkdir(); (drive/'Books').mkdir()
    inventory=[dict(uuid='AA-BB',mount=str(drive),name='Travel',filesystem='exfat')]
    return home,drive,inventory

def add(setup,role='travel'):
    h,d,i=setup
    return s.register(str(d),'Travel',role,['Books'] if role=='travel' else [],h,i,True)['registration']

def test_preview_has_no_side_effects(setup):
    h,d,i=setup
    plan=s.register(str(d),'Travel','travel',['Books'],h,i)
    assert plan['preserved'] and not (d/s.MARKER).exists() and not h.exists()

def test_move_to_new_host_and_mount_offline(setup,tmp_path,monkeypatch):
    h,d,i=setup; record=add(setup)
    other=tmp_path/'other-account'; moved=tmp_path/'different mount'
    d.rename(moved)
    s.merge([record],other)
    monkeypatch.setattr(s.platform,'system',lambda:'Linux' if record['platform']=='Darwin' else 'Darwin')
    data=s.scan(other,[dict(i[0],mount=str(moved),uuid='different-OS-UUID')])
    assert data['attached'][0]['state']=='available'
    assert s.resolve(data,'Travel')==[str(moved/'Books')]
    assert s.scan(other,[])['attached']==[]
    with pytest.raises(ValueError,match='disconnected'):s.resolve(s.scan(other,[]),'Travel')

def test_unknown_marker_not_automatically_trusted(setup,tmp_path):
    h,d,i=setup;add(setup)
    assert s.scan(tmp_path/'unknown',i)['attached'][0]['state'].startswith('unregistered')

def test_backup_repository_and_configuration_unchanged(setup):
    h,d,i=setup
    repo=d/'FabricRecovery';repo.mkdir();(repo/'destination.json').write_text('existing marker')
    config=h/'.config/future-crash-look/recovery';config.mkdir(parents=True)
    (config/'config.json').write_text('existing config');(config/'key').write_text('secret')
    add(setup,'backup')
    assert (repo/'destination.json').read_text()=='existing marker'
    assert (config/'config.json').read_text()=='existing config'
    assert 'secret' not in (d/s.MARKER).read_text()
    with pytest.raises(ValueError,match='credentials'):s.resolve(s.scan(h,i),'Travel')

def test_replaced_filesystem_and_duplicate_clone_rejected(setup,tmp_path):
    h,d,i=setup; add(setup)
    assert s.scan(h,[dict(i[0],uuid='new')])['attached'][0]['state']=='filesystem identity changed'
    clone=tmp_path/'clone';shutil.copytree(d,clone)
    data=s.scan(h,[*i,dict(i[0],mount=str(clone))])
    assert all(r['state']=='duplicate identity' for r in data['attached'])
    with pytest.raises(ValueError):s.resolve(data,'Travel')

@pytest.mark.parametrize('folder',['../outside','/absolute','.'])
def test_paths_cannot_escape(setup,folder):
    h,d,i=setup
    with pytest.raises(ValueError):s.register(str(d),'Travel','travel',[folder],h,i,True)
    assert not (d/s.MARKER).exists()

def test_symlink_escape_and_marker_overwrite_rejected(setup,tmp_path):
    h,d,i=setup;outside=tmp_path/'outside';outside.mkdir();(d/'Link').symlink_to(outside)
    with pytest.raises(ValueError):s.register(str(d),'Travel','travel',['Link'],h,i,True)
    add(setup)
    with pytest.raises(ValueError,match='already'):add(setup)

def test_peer_merge_conflict_preserves_original(setup):
    h,d,i=setup;r=add(setup);changed=dict(r,name='Changed')
    with pytest.raises(ValueError,match='Conflicting'):s.merge([changed],h)
    assert s.registry(h)==[r]

def test_only_trusted_peers_sync_and_stale_paths_not_used(setup,tmp_path,monkeypatch):
    h,d,i=setup;r=add(setup);new=tmp_path/'new'
    monkeypatch.setattr(s,'drives',lambda:[])
    calls=[]
    def fetch(peer,path):
        calls.append(peer['name']);return dict(registered=[r],attached=[dict(id=r['id'],state='available',folders=['/old'])],checked_at=0)
    result=s.refresh([dict(name='unknown',trusted=False),dict(name='trusted',trusted=True)],fetch,new)
    assert calls==['trusted'] and s.registry(new)==[r]
    assert result['peers'][0]['attached']==[]
    with pytest.raises(ValueError):s.resolve(result,'Travel')

def test_remote_resolution_and_duplicate_hosts_fail_closed(setup):
    h,d,i=setup;r=add(setup);remote=s.scan(h,i)
    data=dict(registered=[r],attached=[],peers=[dict(node='host',attached=remote['attached'])])
    assert s.resolve(data,'Travel')==['@host:'+str(d/'Books')]
    data['attached']=remote['attached']
    with pytest.raises(ValueError):s.resolve(data,'Travel')

def test_expired_cache_never_exposes_old_routes(monkeypatch):
    monkeypatch.setattr(s,'_CACHE',dict(registered=[],attached=[{'mount':'/old'}],peers=[],checked_at=0))
    assert s.snapshot()['attached']==[]

def test_readonly_travel_discovery_preserves_backup_filter(monkeypatch):
    from core import recovery_setup as r
    from types import SimpleNamespace
    data={'blockdevices':[dict(name='drive',uuid='ID',ro=True,tran='usb',mountpoints=['/media/travel'])]}
    monkeypatch.setattr(r.sys,'platform','linux')
    monkeypatch.setattr(r,'command',lambda _:json.dumps(data))
    monkeypatch.setattr(Path,'is_mount',lambda _:True)
    monkeypatch.setattr(r.os,'statvfs',lambda _:SimpleNamespace(f_flag=r.os.ST_RDONLY))
    monkeypatch.setattr(r.shutil,'disk_usage',lambda _:SimpleNamespace(total=10,free=5))
    assert r.mounted_drives()==[]
    assert r.mounted_drives(include_readonly=True)[0]['uuid']=='ID'

def test_cli_preview_and_resolve(setup,monkeypatch,capsys):
    h,d,i=setup;monkeypatch.setattr(s,'drives',lambda:i)
    monkeypatch.setattr(s,'config_dir',lambda home=None:h/'storage')
    assert s.main(['register','--mount',str(d),'--name','Travel','--role','travel','--path','Books'])==0
    assert 'No changes made' in capsys.readouterr().out
    assert s.main(['register','--mount',str(d),'--name','Travel','--role','travel','--path','Books','--yes'])==0
    monkeypatch.setattr(s,'request',lambda path:s.scan(inventory=i))
    assert s.main(['resolve','Travel'])==0
    assert str(d/'Books') in capsys.readouterr().out
