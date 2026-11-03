import importlib.machinery
import importlib.util
import io
import json
import os
from pathlib import Path
import sys
import time
from unittest.mock import Mock

import pytest

ROOT=Path(__file__).resolve().parents[1]

@pytest.fixture
def lk(monkeypatch):
    loader=importlib.machinery.SourceFileLoader('lk_responsive',str(ROOT/'look/lk'))
    spec=importlib.util.spec_from_loader(loader.name,loader)
    module=importlib.util.module_from_spec(spec);loader.exec_module(module)
    monkeypatch.setattr(module,'_MEDIA_CATALOG_LOCAL_NAMES',set())
    return module


def test_node_identity_is_reused_then_expires(lk,monkeypatch):
    now=[100.0]
    monkeypatch.setattr(lk.time,'monotonic',lambda:now[0])
    response=Mock()
    response.__enter__=Mock(return_value=io.BytesIO(b'{"name":"test-owner"}'))
    response.__exit__=Mock(return_value=False)
    request=Mock(return_value=response)
    monkeypatch.setattr(lk.urllib.request,'urlopen',request)
    assert 'test-owner' in lk._media_local_node_names()
    for _ in range(100):assert 'test-owner' in lk._media_local_node_names()
    assert request.call_count==1
    now[0]+=31
    response.__enter__.return_value=io.BytesIO(b'{"name":"new-owner"}')
    assert 'new-owner' in lk._media_local_node_names()
    assert request.call_count==2


def test_queue_view_is_bounded_and_marks_playing_item(lk,monkeypatch):
    monkeypatch.setattr(lk.shutil,'get_terminal_size',lambda *_:os.terminal_size((60,12)))
    snap={'index':5,'session':{'queue':[{'title':f'Track {i}'} for i in range(30)]}}
    text=lk._strip_ansi(lk._media_player_queue_render(snap))
    assert '▶   6  Track 5' in text
    assert 'Track 12' not in text
    assert 'Q back' in text
    assert len(text.splitlines())<=12
    assert 'Track 29' in lk._media_player_queue_render(snap,100)


def test_player_render_does_not_persist_queue(lk,monkeypatch):
    snap=Mock(return_value=None)
    monkeypatch.setattr(lk,'_media_status_snapshot',snap)
    lk._media_player_render(show_queue=True)
    snap.assert_called_once_with(read_only=True)


def test_child_action_keeps_input_free_and_rejects_overlap():
    sys.path.insert(0,str(ROOT/'look'))
    from media_ui_work import MediaAction
    action=MediaAction()
    try:
        assert action.start([sys.executable,'-c','import sys,time,json; x=json.load(sys.stdin); time.sleep(.15); print(x[0]["title"])'],[{'title':'Selected song'}])
        assert action.busy
        assert action.poll() is None
        assert not action.start([],[])
        deadline=time.monotonic()+5
        while time.monotonic()<deadline:
            result=action.poll()
            if result is not None:break
            time.sleep(.01)
        assert result==(0,'Selected song')
        assert not action.busy
    finally:action.close()


def test_mercury_theme_matches_reader_and_has_readable_inks():
    from look import terminal_style as styles
    palette=styles.THEMES['mercury']
    assert palette['background']=='#f5f0e5'
    assert palette['foreground']=='#233342'
    assert palette['url_color']=='#315c80'
    for value in palette['accents'].values():
        assert styles.contrast(palette['background'],value)>=4.5


def test_append_skips_unreachable_rows_before_mutating_queue(lk,monkeypatch,capsys):
    selected=[{'id':'missing'},{'id':'present'}]
    monkeypatch.setattr(sys,'stdin',io.StringIO(json.dumps(selected)))
    monkeypatch.setattr(lk,'_media_pin_playable_rows',lambda rows:([rows[1]],[('missing','404')]))
    append=Mock(return_value=1)
    monkeypatch.setattr(lk,'_media_queue_append',append)
    monkeypatch.setattr(lk,'_media_queue_notice',lambda count:f'queued {count}')
    assert lk.media(['_desk-action','append'])==0
    append.assert_called_once_with([selected[1]])
    assert '1 unavailable item(s) skipped' in capsys.readouterr().out


def test_invalid_child_payload_cannot_modify_queue(lk,monkeypatch):
    monkeypatch.setattr(sys,'stdin',io.StringIO('{"path":"not a selection"}'))
    launch=Mock()
    monkeypatch.setattr(lk,'_media_launch_from_library',launch)
    assert lk.media(['_desk-action','play'])==1
    launch.assert_not_called()


def test_child_failure_receipt_survives_exit():
    from media_ui_work import MediaAction
    action=MediaAction()
    try:
        action.start([sys.executable,'-c','import sys; print("source unavailable",file=sys.stderr); sys.exit(1)'],[])
        deadline=time.monotonic()+5
        result=None
        while time.monotonic()<deadline and result is None:
            result=action.poll();time.sleep(.01)
        assert result==(1,'source unavailable')
    finally:action.close()
