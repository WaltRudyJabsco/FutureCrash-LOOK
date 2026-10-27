from unittest.mock import Mock
import pytest
from test_media_request_regressions import lk


@pytest.mark.parametrize('position,audio,video,expected',[
    (None,None,None,False), # opening a URL is not proof of playback
    (0,None,None,False),
    (None,{'format':'mp3'},None,False),
    (0,{'format':'mp3'},None,True),
    (12.5,None,{'w':1920,'h':1080},True),
])
def test_loaded_requires_clock_and_decoder(lk,monkeypatch,position,audio,video,expected):
    monkeypatch.setattr(lk,'_media_mpv_alive',lambda:True)
    props={'idle-active':False,'time-pos':position,'audio-params':audio,'video-params':video}
    monkeypatch.setattr(lk,'_media_mpv_property',props.get)
    assert lk._media_mpv_loaded() is expected


def test_loading_is_not_reconciled_to_playing(lk,monkeypatch):
    monkeypatch.setattr(lk,'_media_mpv_alive',lambda:True)
    monkeypatch.setattr(lk,'_media_mpv_loaded',lambda:False)
    props={'playlist-pos':0,'idle-active':False,'pause':False}
    monkeypatch.setattr(lk,'_media_mpv_property',props.get)
    monkeypatch.setattr(lk,'_media_save_session',lambda value:value)
    state=lk._media_sync_session({'queue':[{'path':'/song.mp3'}],'state':'playing'})
    assert state['state']=='loading' and state['duration'] is None


def test_dead_loading_worker_becomes_stopped(lk,monkeypatch):
    monkeypatch.setattr(lk,'_media_mpv_alive',lambda:False)
    monkeypatch.setattr(lk,'_media_save_session',lambda value:value)
    assert lk._media_sync_session({'state':'loading','pid':999})=={'state':'stopped'}


def test_transport_does_not_invent_a_zero_duration(lk):
    lines=lk._media_mp_transport_lines({'state':'loading','position':None,'duration':None},80)
    assert '--:-- / --:--' in lk._strip_ansi('\n'.join(lines))


def test_startup_timeout_does_not_report_ready(lk,monkeypatch):
    clock=iter([0,0,1,2,3,4])
    monkeypatch.setattr(lk.time,'monotonic',lambda:next(clock))
    monkeypatch.setattr(lk.time,'sleep',lambda *_:None)
    monkeypatch.setattr(lk,'_media_mpv_loaded',lambda:False)
    monkeypatch.setattr(lk,'_media_tail_player_log',lambda *_:['Failed to open source'])
    process=Mock();process.poll.return_value=None
    assert not lk._media_wait_for_mpv_start(process,timeout=.1)
    process.terminate.assert_called_once()
