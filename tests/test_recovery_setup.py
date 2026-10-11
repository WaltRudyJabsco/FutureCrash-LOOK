"""New-account onboarding, mount identity, schedule isolation and failure recovery."""
import io
import json
from pathlib import Path
import plistlib
import shutil
from types import SimpleNamespace
from unittest.mock import Mock
import pytest
from core import recovery as r, recovery_setup as s


@pytest.fixture
def home(tmp_path):
    path = tmp_path / 'new account'; path.mkdir(); return path


def test_linux_discovers_only_writable_mounted_external_volumes(monkeypatch):
    disks = {'blockdevices': [
        {'name':'sda','tran':'usb','children':[
            {'name':'sda1','uuid':'ABCD-1234','label':'Family Backup','fstype':'exfat','mountpoints':['/media/Family Backup']},
            {'name':'sda2','uuid':'locked','mountpoints':[None]},
            {'name':'sda3','uuid':'readonly','ro':True,'mountpoints':['/media/readonly']}]},
        {'name':'nvme0','children':[{'name':'root','uuid':'ROOT','mountpoints':['/']}]}]}
    monkeypatch.setattr(s.sys,'platform','linux')
    monkeypatch.setattr(s,'command',lambda argv:json.dumps(disks))
    monkeypatch.setattr(Path,'is_mount',lambda path:True)
    monkeypatch.setattr(s.os,'statvfs',lambda path:SimpleNamespace(f_flag=0))
    monkeypatch.setattr(s.shutil,'disk_usage',lambda path:SimpleNamespace(total=1000,free=900))
    rows = s.mounted_drives()
    assert len(rows)==1 and rows[0]['mount']=='/media/Family Backup' and rows[0]['uuid']=='ABCD-1234'


def test_mac_discovers_external_apfs_volume_not_system_or_locked(monkeypatch):
    info = {'disk1':{'Internal':True,'MountPoint':'/','VolumeUUID':'root'},
            'disk2':{'Internal':False,'MountPoint':'/Volumes/日本語','VolumeUUID':'ABCD-1234','VolumeName':'Family'},
            'disk3':{'Internal':False,'VolumeUUID':'locked'}}
    def command(argv,**kw):
        return plistlib.dumps({'AllDisks':list(info)} if 'list' in argv else info[argv[-1]])
    monkeypatch.setattr(s.sys,'platform','darwin');monkeypatch.setattr(s,'command',command)
    monkeypatch.setattr(Path,'is_mount',lambda path:True)
    monkeypatch.setattr(s.os,'statvfs',lambda path:SimpleNamespace(f_flag=0))
    monkeypatch.setattr(s.shutil,'disk_usage',lambda path:SimpleNamespace(total=1000,free=900))
    assert s.mounted_drives()[0]['mount']=='/Volumes/日本語'
    assert r.mount_for('abcd-1234')==Path('/Volumes/日本語')


def test_mac_duplicate_uuid_rejected(monkeypatch):
    monkeypatch.setattr(r.sys,'platform','darwin')
    monkeypatch.setattr(s,'mounted_drives',lambda **kw:[{'uuid':'ABCD','mount':'/Volumes/a'},{'uuid':'ABCD','mount':'/Volumes/b'}])
    with pytest.raises(ValueError,match='exactly one'):r.mount_for('ABCD')


def test_key_copy_private_exclusive_and_not_on_backup_drive(home,tmp_path,monkeypatch):
    state=r.root(home);state.mkdir(parents=True);key=state/'key';key.write_text('fixture');key.chmod(0o600)
    volume=tmp_path/'volume';volume.mkdir()
    monkeypatch.setattr(r,'checked_repository',lambda home:volume/'FabricRecovery/repository')
    spare=tmp_path/'spare.key'
    assert s.copy_key(home,spare)==str(spare)
    assert spare.read_text()=='fixture' and spare.stat().st_mode&0o777==0o600
    with pytest.raises(ValueError,match='new file'):s.copy_key(home,spare)
    with pytest.raises(ValueError,match='away'):s.copy_key(home,volume/'key')


def test_accounts_on_same_machine_have_separate_snapshot_owners(home,tmp_path,monkeypatch):
    other=tmp_path/'another';other.mkdir()
    assert r.capsule_owner(home)!=r.capsule_owner(other)
    identity=home/'.config/future-crash-look/identity/node_ed25519.pub';identity.parent.mkdir(parents=True);identity.write_text('public fixture')
    owner=r.capsule_owner(home)
    moved=tmp_path/'moved';shutil.copytree(home,moved)
    monkeypatch.setattr(r.socket,'gethostname',lambda:'renamed-computer')
    assert r.capsule_owner(moved)==owner


def test_unprepared_ssh_source_is_rejected_before_any_initialization(home,monkeypatch):
    monkeypatch.setattr(s.shutil,'which',lambda name:'/bin/restic')
    monkeypatch.setattr(s,'check_source',Mock(side_effect=ValueError('SSH not ready')))
    init=Mock();monkeypatch.setattr(r,'initialize',init)
    with pytest.raises(ValueError,match='SSH not ready'):s.configure(home,mount='/vol',key_copy='/spare',sources=['wife_account@her-mac'])
    init.assert_not_called();assert not r.root(home).exists()


def test_manual_schedule_does_not_require_an_existing_systemd_unit(home,monkeypatch):
    monkeypatch.setattr(s.sys,'platform','linux')
    run=Mock();monkeypatch.setattr(s.subprocess,'run',run)
    s.schedule(home,False);run.assert_not_called()


@pytest.mark.parametrize('platform',['linux','darwin'])
def test_generated_schedule_uses_only_current_home_and_generic_runner(home,monkeypatch,platform):
    monkeypatch.setattr(s.sys,'platform',platform)
    run=Mock(return_value=SimpleNamespace(returncode=0,stderr=''));monkeypatch.setattr(s.subprocess,'run',run)
    s.schedule(home,True)
    if platform=='darwin':
        data=plistlib.loads((home/'Library/LaunchAgents'/f'{s.MAC_LABEL}.plist').read_bytes())
        assert data['ProgramArguments']==[str(home/'.local/bin/fcl-recovery'),'scheduled']
        assert data['StartInterval']==3600 and data['Umask']==0o077
    else:
        data=(home/f'.config/systemd/user/{s.SERVICE}.service').read_text()
        assert f'"{home}/.local/bin/fcl-recovery" scheduled' in data
        assert '@' not in data and '3090' not in data


def test_disconnected_schedule_skips_sources(home,monkeypatch):
    r.private_json(r.root(home)/'setup.json',{'ready':True,'sources':['wife@mac']})
    monkeypatch.setattr(r,'checked_repository',lambda home:None)
    collect=Mock();monkeypatch.setattr(s,'collect_local',collect)
    assert s.run_configured(home)=={'skipped':'backup drive disconnected'}
    collect.assert_not_called()


def test_incomplete_setup_cannot_run_in_background(home,monkeypatch):
    r.private_json(r.root(home)/'setup.json',{'ready':False,'sources':[]})
    backup=Mock();monkeypatch.setattr(r,'backup',backup)
    assert 'setup needs' in s.run_configured(home)['skipped'];backup.assert_not_called()


def test_one_offline_source_does_not_stop_other_sources(home,monkeypatch):
    r.private_json(r.root(home)/'setup.json',{'ready':True,'sources':['a@first','b@second']})
    monkeypatch.setattr(r,'checked_repository',lambda home:home)
    monkeypatch.setattr(r,'backup',lambda *args,**kw:{'restore_tested':True})
    def collect(home,source,due):
        if source=='a@first':raise ValueError('offline')
        return {'restore_tested':True}
    monkeypatch.setattr(s,'collect_local',collect)
    result=s.run_configured(home)
    assert not result['verified'] and len(result['results'])==2 and result['errors'][0]['source']=='a@first'


def test_cancelled_wizard_never_creates_configuration(home,monkeypatch):
    monkeypatch.setattr(s.shutil,'which',lambda name:'/bin/restic')
    monkeypatch.setattr(s,'mounted_drives',lambda:[{'name':'Backup','mount':'/Volumes/Backup','bytes':1000,'free_bytes':900}])
    monkeypatch.setattr('builtins.input',lambda prompt:'')
    assert s.wizard(home)=={'cancelled':True};assert not r.root(home).exists()


def test_failed_initialization_cleans_only_its_new_directory(home,tmp_path,monkeypatch):
    volume=tmp_path/'volume';volume.mkdir();ordinary=volume/'family-photo';ordinary.write_text('keep')
    monkeypatch.setattr(r,'mount_for',lambda uuid:volume)
    monkeypatch.setattr(Path,'is_mount',lambda path:True)
    monkeypatch.setattr(r.shutil,'which',lambda name:'/bin/restic')
    monkeypatch.setattr(r,'restic',Mock(side_effect=RuntimeError('engine failed')))
    with pytest.raises(RuntimeError,match='engine failed'):r.initialize(home,'ABCD-1234')
    assert ordinary.read_text()=='keep'
    assert not (volume/'FabricRecovery').exists() and not (r.root(home)/'key').exists()


@pytest.mark.skipif(not shutil.which('restic'),reason='Restic required')
def test_fresh_account_setup_real_backup_restore_and_schedule(home,tmp_path,monkeypatch):
    volume=tmp_path/'Family Backup';volume.mkdir();(volume/'ordinary.txt').write_text('keep')
    note=home/'.local/share/look/notebook/notes/a.md';note.parent.mkdir(parents=True);note.write_text('Café 日本語')
    monkeypatch.setattr(s,'mounted_drives',lambda **kw:[{'uuid':'ABCD-1234','mount':str(volume)}])
    monkeypatch.setattr(r,'mount_for',lambda uuid:volume)
    monkeypatch.setattr(Path,'is_mount',lambda path:True)
    scheduler=Mock();monkeypatch.setattr(s,'schedule',scheduler)
    spare=tmp_path/'wife-spare.key'
    report=s.configure(home,mount=str(volume),key_copy=str(spare),daily=True)
    assert report['verified'] and report['results'][0]['restore_tested']
    assert report['scheduled'];scheduler.assert_called_once_with(home,True)
    assert json.loads((r.root(home)/'setup.json').read_text())['ready']
    assert (volume/'ordinary.txt').read_text()=='keep'
    restored=tmp_path/'recovered';r.restore(home,restored)
    assert (restored/'home/.local/share/look/notebook/notes/a.md').read_text()=='Café 日本語'
    assert s.run_configured(home)['results'][0]['skipped']=='daily recovery already verified'


def test_failed_restore_verification_never_enables_schedule(home,tmp_path,monkeypatch):
    r.private_json(r.root(home)/'destination.json',{'uuid':'ABCD-1234'})
    monkeypatch.setattr(s.shutil,'which',lambda name:'/bin/restic')
    monkeypatch.setattr(s,'run_configured',lambda *args,**kw:{'verified':False,'results':[],'errors':[{'source':'this computer','error':'failed restore'}]})
    scheduler=Mock();monkeypatch.setattr(s,'schedule',scheduler)
    report=s.configure(home)
    assert not report['scheduled'];scheduler.assert_not_called()
    assert not json.loads((r.root(home)/'setup.json').read_text())['ready']


@pytest.mark.parametrize('target',['-oProxyCommand=evil','someone@host;rm','host','wife@host\n'])
def test_ssh_target_rejects_options_and_shell_text(target):
    with pytest.raises(ValueError):s.ssh_target(target)


def test_mac_ignores_writable_disk_images_and_readonly_volumes(monkeypatch):
    info={'image':{'Internal':False,'MountPoint':'/Volumes/Image','VolumeUUID':'image','BusProtocol':'Disk Image','WritableVolume':True},
          'readonly':{'Internal':False,'MountPoint':'/Volumes/Readonly','VolumeUUID':'read','WritableVolume':False}}
    monkeypatch.setattr(s.sys,'platform','darwin')
    monkeypatch.setattr(s,'command',lambda argv,**kw:plistlib.dumps({'AllDisks':list(info)} if 'list' in argv else info[argv[-1]]))
    assert s.mounted_drives()==[]


def test_advertisement_exposes_no_keys_accounts_or_drive_identifiers(home,monkeypatch):
    from core import node
    monkeypatch.setattr(Path,'home',lambda:home)
    r.private_json(r.root(home)/'destination.json',{'uuid':'ABCD','private':'do not advertise'})
    r.private_json(r.root(home)/'setup.json',{'ready':False,'sources':['wife@private-host'],'key_copy':'/private/key'})
    assert node._recovery_advertisement()=={'destination':True,'scope':'fabric-essential','setup_complete':False}


def test_setup_does_not_treat_a_skipped_first_backup_as_verified(home,monkeypatch):
    r.private_json(r.root(home)/'destination.json',{'uuid':'ABCD-1234'})
    monkeypatch.setattr(s.shutil,'which',lambda name:'/bin/restic')
    monkeypatch.setattr(s,'run_configured',lambda *args,**kw:{'verified':True,'results':[{'source':'this computer','skipped':'backup already running'}],'errors':[]})
    scheduler=Mock();monkeypatch.setattr(s,'schedule',scheduler)
    result=s.configure(home)
    assert not result['verified'] and not result['scheduled'];scheduler.assert_not_called()


def test_wizard_explains_scope_and_passes_only_selected_current_accounts(home,monkeypatch,capsys):
    monkeypatch.setattr(s.shutil,'which',lambda name:'/bin/restic')
    monkeypatch.setattr(s,'mounted_drives',lambda:[{'name':'Family Drive','mount':'/Volumes/Family','bytes':10**9,'free_bytes':9*10**8}])
    monkeypatch.setattr(s,'peer_choices',lambda:[{'name':'Her Laptop','host':'her-laptop.example'}])
    answers=iter(['1',str(home/'spare.key'),'1','her_account','n','yes'])
    monkeypatch.setattr('builtins.input',lambda prompt:next(answers))
    configure=Mock(return_value={'verified':True});monkeypatch.setattr(s,'configure',configure)
    s.wizard(home)
    configure.assert_called_once_with(home,mount='/Volumes/Family',key_copy=str(home/'spare.key'),sources=['her_account@her-laptop.example'],daily=False)
    output=capsys.readouterr().out
    assert 'Documents, photos and media are not included' in output
    assert 'Family Drive' in output and 'manual' in output


def test_legacy_restore_still_selects_old_local_owner(home,tmp_path,monkeypatch):
    monkeypatch.setattr(r,'checked_repository',lambda home:tmp_path)
    calls=[]
    def restic(home,repo,*args):
        calls.append(args)
        if args[0]=='snapshots':return '[]'
        folder=Path(args[args.index('--target')+1])/'capsule'
        folder.mkdir();(folder/'home').mkdir();r.private_json(folder/'manifest.json',{'schema':1,'files':[]})
        return ''
    monkeypatch.setattr(r,'restic',restic)
    r.restore(home,tmp_path/'recovered')
    assert calls[1][calls[1].index('--host')+1]==r.socket.gethostname()


def test_source_ssh_probe_uses_verified_host_keys_and_no_shell_interpolation(monkeypatch):
    run=Mock(return_value=SimpleNamespace(returncode=0,stdout='{"files":2}',stderr=''))
    monkeypatch.setattr(s.subprocess,'run',run)
    assert s.check_source('her_account@her-laptop.example')['files']==2
    argv=run.call_args.args[0]
    assert 'StrictHostKeyChecking=yes' in argv and 'BatchMode=yes' in argv
    assert argv[-2:]==['her_account@her-laptop.example','~/.local/bin/fcl-recovery inventory']


def test_add_requires_terminal_or_explicit_choices(home,monkeypatch,capsys):
    monkeypatch.setattr(Path,'home',lambda:home)
    monkeypatch.setattr(r.sys.stdin,'isatty',lambda:False)
    assert r.main(['add'])==1
    assert '--yes --mount PATH --key-copy NEW_FILE' in capsys.readouterr().out
    assert not r.root(home).exists()


def test_existing_add_json_never_reinitializes(home,monkeypatch,capsys):
    monkeypatch.setattr(Path,'home',lambda:home)
    r.private_json(r.root(home)/'destination.json',{'uuid':'ABCD'})
    init=Mock();monkeypatch.setattr(r,'initialize',init)
    assert r.main(['add','--json'])==0
    assert json.loads(capsys.readouterr().out)['already_configured'];init.assert_not_called()


@pytest.mark.skipif(not shutil.which('restic'),reason='Restic required')
def test_owner_collects_foreign_account_and_verifies_it_locally(home,tmp_path,monkeypatch):
    volume=tmp_path/'volume';volume.mkdir()
    monkeypatch.setattr(r,'mount_for',lambda uuid:volume);monkeypatch.setattr(Path,'is_mount',lambda path:True)
    r.initialize(home,'ABCD')
    foreign=tmp_path/'contributor';note=foreign/'.local/share/look/notebook/notes/b.md';note.parent.mkdir(parents=True);note.write_text('Her notes')
    archive=io.BytesIO();r.stream_capsule(foreign,archive)
    process=SimpleNamespace(stdout=io.BytesIO(archive.getvalue()),wait=lambda **kw:0,poll=lambda:0)
    original_popen=s.subprocess.Popen
    monkeypatch.setattr(s.subprocess,'Popen',lambda argv,**kw:process if argv[0]=='ssh' else original_popen(argv,**kw))
    result=s.collect_local(home,'her_account@her-laptop')
    assert result['restore_tested'] and result['node']==r.capsule_owner(foreign)
    assert result['node']!=r.capsule_owner(home)
    restored=tmp_path/'foreign-restore';r.restore(home,restored,host=result['node'])
    assert (restored/'home/.local/share/look/notebook/notes/b.md').read_text()=='Her notes'
