import gzip
import hashlib
from unittest.mock import Mock

import pytest
from look import force_player as force


def movie():
    return ('2\n'+'\n'.join(['A tiny frame']+['']*12)+'\n'+'15\n'+'\n'.join(['Another frame']+['']*12)+'\n').encode()


def test_frame_timing_and_boundaries():
    frames=force.parse(movie());starts=force.timeline(frames)
    assert len(frames)==2 and starts==[0,2,17]
    assert force.frame_at(starts,0)==0
    assert force.frame_at(starts,2/15)==1
    assert force.frame_at(starts,1000)==1
    assert force.clock_text(1073.5)=='17:53'


@pytest.mark.parametrize('raw',[b'',b'2\npartial',movie().replace(b'2\n',b'0\n',1),movie().replace(b'A tiny frame',b'\x1b[2J'),movie().replace(b'A tiny frame',b'X'*68),b'\xff'])
def test_rejects_malformed_frames_and_terminal_control_sequences(raw):
    with pytest.raises((ValueError,UnicodeError)):force.parse(raw)


def test_fetch_is_verified_atomic_and_cached_for_offline_use(tmp_path,monkeypatch):
    raw=movie();monkeypatch.setattr(force,'SHA256',hashlib.sha256(raw).hexdigest())
    response=Mock();response.read.return_value=raw;response.__enter__=Mock(return_value=response);response.__exit__=Mock()
    fetch=Mock(return_value=response);monkeypatch.setattr(force.urllib.request,'urlopen',fetch)
    path=tmp_path/'cache/movie.gz'
    assert force.ensure_cache(path)[0]==raw
    assert gzip.decompress(path.read_bytes())==raw
    fetch.assert_called_once();fetch.reset_mock(side_effect=AssertionError('Offline playback must not fetch'))
    assert len(force.ensure_cache(path)[1])==2
    fetch.assert_not_called()


def test_failed_refresh_keeps_previous_cache(tmp_path,monkeypatch):
    raw=movie();path=tmp_path/'movie.gz';path.write_bytes(gzip.compress(raw));previous=path.read_bytes()
    response=Mock();response.read.return_value=b'wrong';response.__enter__=Mock(return_value=response);response.__exit__=Mock()
    monkeypatch.setattr(force.urllib.request,'urlopen',Mock(return_value=response))
    with pytest.raises(ValueError,match='checksum'):force.ensure_cache(path,refresh=True)
    assert path.read_bytes()==previous


def test_status_and_about_do_not_download(tmp_path,monkeypatch,capsys):
    monkeypatch.setattr(force,'cache_path',lambda:tmp_path/'missing.gz')
    download=Mock(side_effect=AssertionError('Read-only status must not download'));monkeypatch.setattr(force.urllib.request,'urlopen',download)
    assert force.main(['--status'])==0
    assert force.main(['--about'])==0
    assert 'Simon Jansen' in capsys.readouterr().out
    download.assert_not_called()


def test_pause_seek_resize_and_quit_do_not_change_terminal_data(monkeypatch):
    window=Mock();window.getmaxyx.return_value=(24,90)
    window.get_wch.side_effect=[' ',force.curses.KEY_RIGHT,force.curses.KEY_HOME,'q']
    monkeypatch.setattr(force.curses,'raw',lambda:None);monkeypatch.setattr(force.curses,'curs_set',lambda *args:None)
    monkeypatch.setattr(force.curses,'has_colors',lambda:False)
    ticks=iter(range(30))
    force.player(force.parse(movie()),window,now=lambda:next(ticks)/20)
    assert window.get_wch.call_count==4
    assert any('PAUSED' in str(call) for call in window.addnstr.call_args_list)


def test_player_restores_terminal_after_failure(monkeypatch):
    monkeypatch.setattr(force.sys,'stdin',Mock(fileno=lambda:0))
    monkeypatch.setattr(force.termios,'tcgetattr',lambda fd:['original'])
    restore=Mock();monkeypatch.setattr(force.termios,'tcsetattr',restore)
    monkeypatch.setattr(force.curses,'wrapper',Mock(side_effect=RuntimeError('test failure')))
    with pytest.raises(RuntimeError):force.play(force.parse(movie()))
    assert restore.call_args.args[-1]==['original']
