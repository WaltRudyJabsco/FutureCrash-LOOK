"""Audio/video presentation must not create a second player or mutate catalog rows."""
import importlib.machinery
import importlib.util
import io
import os
import sys
from pathlib import Path

import pytest

ROOT=Path(__file__).resolve().parents[1]

@pytest.fixture
def lk(monkeypatch):
    loader=importlib.machinery.SourceFileLoader('lk_desks_v2',str(ROOT/'look/lk'))
    spec=importlib.util.spec_from_loader(loader.name,loader)
    module=importlib.util.module_from_spec(spec)
    monkeypatch.setitem(sys.modules,loader.name,module)
    loader.exec_module(module)
    return module

@pytest.fixture
def rows():
    return [dict(id='a',title='Music',path='/music/a.mp3',media_type='audio/mpeg'),
            dict(id='p',title='Podcast',path='https://example.test/feed',kind='podcast'),
            dict(id='m',title='Movie',path='/movies/m.mkv'),
            dict(id='t',title='Episode',path='/tv/t.mp4',series='Show',season=2,episode=3),
            dict(id='w',title='Online video',path='https://example.test/watch',kind='video'),
            dict(id='i',title='Picture',path='/photo.jpg',media_type='image/jpeg')]

@pytest.mark.parametrize('kind,ids',[('audio',['a','p']),('video',['m','t','w'])])
@pytest.mark.parametrize('mode',['library','queue'])
def test_desks_filter_without_changing_shared_queue(lk,rows,monkeypatch,kind,ids,mode):
    monkeypatch.setattr(lk,'_media_collapse',lambda rows,**kw:list(rows))
    monkeypatch.setattr(lk,'_media_sync_session',lambda:{'queue':rows})
    result=lk._media_mp_rows(mode,rows,'',kind)
    assert [r['id'] for r in result]==ids
    assert len(rows)==6
    assert all(r is rows[rows.index(r)] for r in result)
    assert lk._media_mp_rows(mode,rows,'does-not-exist',kind)==[]

@pytest.mark.parametrize('command,kind',[('mp','audio'),('tv','video')])
def test_top_level_and_media_alias_dispatch(lk,monkeypatch,command,kind):
    calls=[]
    monkeypatch.setattr(lk,'_media_player_library',lambda query='',media_kind='audio':calls.append((query,media_kind)) or 0)
    monkeypatch.setattr(sys,'argv',['lk',command,'some title'])
    assert lk.main()==0
    monkeypatch.setattr(sys,'argv',['lk','media',command,'some title'])
    assert lk.main()==0
    assert calls==[('some title',kind)]*2

class Terminal(io.StringIO):
    def isatty(self):return True
    def fileno(self):return 0

class Preview:
    enabled=False
    def frame_cleared(self):pass
    def invalidate(self):pass
    def paint_ready(self):pass

@pytest.mark.parametrize('size',[(80,24),(120,34),(60,24)])
@pytest.mark.parametrize('kind',['audio','video'])
def test_frames_fit_and_play_preserves_identity(lk,rows,monkeypatch,size,kind):
    out=Terminal();monkeypatch.setattr(sys,'stdout',out);monkeypatch.setattr(sys,'stdin',Terminal())
    monkeypatch.setattr(lk.termios,'tcgetattr',lambda fd:[])
    monkeypatch.setattr(lk.termios,'tcsetattr',lambda *a:None)
    monkeypatch.setattr(lk.tty,'setcbreak',lambda fd:None)
    monkeypatch.setattr(lk.shutil,'get_terminal_size',lambda *a:os.terminal_size(size))
    monkeypatch.setattr(lk,'NativePreviewController',Preview)
    monkeypatch.setattr(lk,'_media_catalog_entries',lambda:(rows,{'nodes':['local']}))
    monkeypatch.setattr(lk,'_media_collapse',lambda rows,**kw:list(rows))
    monkeypatch.setattr(lk,'_media_status_snapshot',lambda:None)
    monkeypatch.setattr(lk,'_media_cover_lines',lambda *a,**kw:[])
    monkeypatch.setattr(lk,'_media_remote_preview_state',lambda *a:('unavailable',''))
    monkeypatch.setattr(lk,'_media_detail_lines',lambda *a:[])
    keys=iter(['F','G','M','\r','esc'])
    monkeypatch.setattr(lk,'_read_tty_key',lambda *a:next(keys))
    frames=[];original=lk._terminal_frame_payload
    monkeypatch.setattr(lk,'_terminal_frame_payload',lambda frame:frames.append(frame) or original(frame))
    launches=[]
    monkeypatch.setattr(lk,'_media_launch_session',lambda session:launches.append(session))
    assert lk._media_player_library(media_kind=kind)==0
    assert launches and launches[0]['queue'][0]['id'] in ({'a','p'} if kind=='audio' else {'m','t','w'})
    assert 'SORT Title ↓' in lk._strip_ansi(out.getvalue())
    assert 'M image/ASCII' in lk._strip_ansi(out.getvalue())
    for frame in frames:
        lines=frame.split('\n')
        assert len(lines)<=size[1]
        assert all(len(lk._strip_ansi(line))<=size[0] for line in lines)

@pytest.mark.parametrize('kind',['audio','video'])
def test_empty_fresh_catalog_is_useful_and_does_not_launch(lk,monkeypatch,capsys,kind):
    monkeypatch.setattr(lk,'_media_catalog_entries',lambda:([],{}))
    monkeypatch.setattr(lk,'_media_collapse',lambda rows,**kw:list(rows))
    monkeypatch.setattr(lk,'_media_status_snapshot',lambda:None)
    monkeypatch.setattr(lk,'_media_launch_session',lambda *a:pytest.fail('browsing must not play'))
    assert lk._media_player_library(media_kind=kind)==0
    assert kind+' library' in capsys.readouterr().out
