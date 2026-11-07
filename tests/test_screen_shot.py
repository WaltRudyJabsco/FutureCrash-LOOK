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
    assert run.call_args.args[0]==['open','-a','Screenshot']
    run.reset_mock();assert shot.main(['record','--delay','10'])==1;run.assert_not_called()


def test_png_clipboard_declares_image_type(tmp_path,monkeypatch):
    path=tmp_path/'image.png';path.write_bytes(b'png')
    monkeypatch.setattr(shot.sys,'platform','linux');monkeypatch.setenv('WAYLAND_DISPLAY','wayland-0')
    monkeypatch.setattr(shot.shutil,'which',lambda name:name)
    run=Mock();monkeypatch.setattr(shot.subprocess,'run',run)
    shot.copy_image(path)
    assert run.call_args.args[0]==['wl-copy','--type','image/png']


def test_gnome_recording_explains_native_control_without_invalid_dbus(monkeypatch,capsys):
    monkeypatch.setattr(shot.sys,'platform','linux');monkeypatch.setenv('XDG_CURRENT_DESKTOP','ubuntu:GNOME')
    run=Mock();monkeypatch.setattr(shot.subprocess,'run',run)
    assert shot.main(['record'])==0
    assert 'No recording has started' in capsys.readouterr().out
    run.assert_not_called()


def test_uniform_frame_is_not_a_successful_screenshot():
    class Color:
        def __init__(self,value):self.value=value
        def rgba(self):return self.value
    class Frame:
        def isNull(self):return False
        def width(self):return 5120
        def height(self):return 2880
        def pixelColor(self,x,y):return Color(0xff161619)
    assert not shot.varied_frame(Frame())
    class Content(Frame):
        def pixelColor(self,x,y):return Color(x+y)
    assert shot.varied_frame(Content())


def test_native_mac_capture_uses_selected_rectangle(tmp_path,monkeypatch):
    path=tmp_path/'frame.png'
    calls=[]
    def run(args,**kwargs):
        calls.append(args);path.write_bytes(b'png');return Mock(returncode=0,stderr='')
    monkeypatch.setattr(shot.subprocess,'run',run)
    shot.capture_mac((-1920,0,1920,1080),path)
    assert calls==[['/usr/sbin/screencapture','-x','-t','png','-R','-1920,0,1920,1080',str(path)]]


def test_failed_native_capture_stops_before_clipboard(tmp_path,monkeypatch):
    monkeypatch.setattr(shot.subprocess,'run',Mock(return_value=Mock(returncode=1,stderr='capture denied')))
    with pytest.raises(ValueError,match='Nothing copied'):
        shot.capture_mac((0,0,100,100),tmp_path/'absent.png')
