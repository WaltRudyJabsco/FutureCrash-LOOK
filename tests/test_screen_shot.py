from pathlib import Path
from unittest.mock import Mock
import pytest
import screen_shot as shot


def test_selection_is_bounded_and_preserves_requested_order():
    assert shot.selection('all',3)==[0,1,2]
    assert shot.selection('3,1,3',3)==[2,0]
    for bad in ('0','4','-1','1,x',''):
        with pytest.raises(ValueError):shot.selection(bad,3)


def test_wayland_uses_picker_not_invented_monitor_ids(monkeypatch):
    monkeypatch.setattr(shot.sys,'platform','linux');monkeypatch.setenv('WAYLAND_DISPLAY','wayland-0')
    portal=Mock();monkeypatch.setattr(shot,'portal_capture',portal)
    assert shot.main(['2'])==1
    portal.assert_not_called()


def test_wayland_copy_and_explicit_save(tmp_path,monkeypatch):
    monkeypatch.setattr(shot.sys,'platform','linux');monkeypatch.setenv('WAYLAND_DISPLAY','wayland-0')
    monkeypatch.setattr(shot,'portal_capture',lambda path:path.write_bytes(b'fake-png'))
    copy=Mock();monkeypatch.setattr(shot,'copy_image',copy)
    output=tmp_path/'saved.png'
    assert shot.main(['--save',str(output)])==0
    assert output.read_bytes()==b'fake-png';copy.assert_called_once()
    assert shot.main(['--save',str(output)])==1
    assert output.read_bytes()==b'fake-png'


def test_recording_only_opens_native_toolbar(monkeypatch):
    monkeypatch.setattr(shot.sys,'platform','darwin')
    run=Mock(return_value=Mock(returncode=0));monkeypatch.setattr(shot.subprocess,'run',run)
    assert shot.main(['record'])==0
    assert run.call_args.args[0]==['/usr/sbin/screencapture','-i','-U','-J','video']
    run.reset_mock();assert shot.main(['record','--delay','10'])==1;run.assert_not_called()


def test_png_clipboard_declares_image_type(tmp_path,monkeypatch):
    path=tmp_path/'image.png';path.write_bytes(b'png')
    monkeypatch.setattr(shot.sys,'platform','linux');monkeypatch.setenv('WAYLAND_DISPLAY','wayland-0')
    monkeypatch.setattr(shot.shutil,'which',lambda name:name)
    run=Mock();monkeypatch.setattr(shot.subprocess,'run',run)
    shot.copy_image(path)
    assert run.call_args.args[0]==['wl-copy','--type','image/png']
