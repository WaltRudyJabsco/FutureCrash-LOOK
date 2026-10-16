import importlib.machinery
import importlib.util
from pathlib import Path
import pytest

ROOT=Path(__file__).resolve().parents[1]

@pytest.fixture
def lk(tmp_path,monkeypatch):
    loader=importlib.machinery.SourceFileLoader('lk_audio_recovery',str(ROOT/'look/lk'))
    spec=importlib.util.spec_from_loader(loader.name,loader)
    module=importlib.util.module_from_spec(spec);loader.exec_module(module)
    monkeypatch.setattr(module,'MEDIA_LAUNCH_LOG',tmp_path/'launch.log')
    return module


def test_explicit_audio_reset_only_reopens_owned_player(lk,monkeypatch):
    commands=[]
    monkeypatch.setattr(lk,'_media_mpv_alive',lambda:True)
    monkeypatch.setattr(lk,'_media_mpv_request',lambda c:commands.append(c) or {'error':'success'})
    ok,message=lk._media_reset_audio()
    assert ok and 'system default' in message
    assert commands==[['set_property','audio-device','auto'],['ao-reload']]
    assert not any(c[0] in {'loadfile','loadlist','seek','quit'} or 'pause' in c for c in commands)


@pytest.mark.parametrize('alive',[False,True])
def test_reset_does_not_claim_success_without_player_receipt(lk,monkeypatch,alive):
    monkeypatch.setattr(lk,'_media_mpv_alive',lambda:alive)
    monkeypatch.setattr(lk,'_media_mpv_request',lambda c:{'error':'unavailable'})
    assert lk._media_reset_audio()[0] is False


@pytest.mark.parametrize('paused,device,platform,reload',[(True,'auto','darwin',True),(False,'auto','darwin',False),(True,'coreaudio/chosen','darwin',False),(True,'auto','linux',False)])
def test_resume_refreshes_only_automatic_mac_output(lk,monkeypatch,paused,device,platform,reload):
    commands=[]
    monkeypatch.setattr(lk.sys,'platform',platform)
    monkeypatch.setattr(lk,'_media_session',lambda:{'queue':[]})
    monkeypatch.setattr(lk,'_media_mpv_alive',lambda:True)
    monkeypatch.setattr(lk,'_media_mpv_property',lambda key:paused if key=='pause' else device)
    monkeypatch.setattr(lk,'_media_mpv_request',lambda c:commands.append(c) or {'error':'success'})
    monkeypatch.setattr(lk,'_media_sync_session',lambda *a:None)
    monkeypatch.setattr(lk.time,'sleep',lambda *a:None)
    assert lk._media_control_session('toggle')==0
    assert (['ao-reload'] in commands)==reload
    assert commands[-1]==['cycle','pause']


@pytest.mark.parametrize('code',[0,1])
def test_library_keeps_failed_launch_receipt_visible_and_private(lk,monkeypatch,code):
    def launch(session):
        print('Could not launch selected player' if code else 'queue loaded')
        return code
    monkeypatch.setattr(lk,'_media_launch_session',launch)
    notice=lk._media_launch_from_library([{'title':'Track','path':'/music/track.m4a'}])
    if code:assert notice.startswith('Playback failed') and 'Could not launch' in notice
    else:assert notice=='playing 1 item(s)'
    assert lk.MEDIA_LAUNCH_LOG.read_text().strip()==('Could not launch selected player' if code else 'queue loaded')
    assert lk.MEDIA_LAUNCH_LOG.stat().st_mode&0o777==0o600
