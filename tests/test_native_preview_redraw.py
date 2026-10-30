import struct
import threading
import time

import look_renderer


def wait_for(predicate):
    deadline=time.monotonic()+2
    while not predicate() and time.monotonic()<deadline:time.sleep(.005)
    assert predicate()


def test_prepared_preview_survives_redraw_without_another_worker_trip(tmp_path,monkeypatch,capsys):
    monkeypatch.setenv('KITTY_WINDOW_ID','test')
    monkeypatch.setenv('LOOK_NATIVE_PREVIEW','on')
    image=tmp_path/'cover.png'
    image.write_bytes(b'\x89PNG\r\n\x1a\n'+b'\0\0\0\rIHDR'+struct.pack('>II',16,16))
    calls=[]
    def prepare(self,path,stamp,rows,cols):calls.append(path);return path
    monkeypatch.setattr(look_renderer.NativePreviewController,'_prepare',prepare)
    controller=look_renderer.NativePreviewController()
    controller.request(image,5,60,10,30)
    wait_for(lambda:controller._ready is not None)
    controller.paint_ready();capsys.readouterr()
    for _ in range(8):
        controller.frame_cleared();capsys.readouterr()
        controller.request(image,5,60,10,30)
        # Image is restored synchronously, before the UI waits for another key.
        assert '\x1b_Ga=T' in capsys.readouterr().out
    assert calls==[image]
    image.write_bytes(image.read_bytes()+b'changed')
    controller.frame_cleared();capsys.readouterr()
    controller.request(image,5,60,10,30)
    wait_for(lambda:len(calls)==2)


def test_obsolete_preparation_can_be_reused_but_never_painted_for_another_item(tmp_path,monkeypatch,capsys):
    monkeypatch.setenv('KITTY_WINDOW_ID','test')
    monkeypatch.setenv('LOOK_NATIVE_PREVIEW','on')
    a=tmp_path/'a.png';b=tmp_path/'b.png'
    data=b'\x89PNG\r\n\x1a\n'+b'\0\0\0\rIHDR'+struct.pack('>II',16,16)
    a.write_bytes(data);b.write_bytes(data)
    entered=threading.Event();release=threading.Event();calls=[]
    def prepare(self,path,stamp,rows,cols):
        calls.append(path);entered.set();release.wait(2);return path
    monkeypatch.setattr(look_renderer.NativePreviewController,'_prepare',prepare)
    controller=look_renderer.NativePreviewController()
    try:
        controller.request(a,5,60,10,30);assert entered.wait(1)
        controller.frame_cleared();capsys.readouterr()
        release.set();wait_for(lambda:controller._prepared is not None)
        controller.paint_ready();assert capsys.readouterr().out==''
        controller.request(a,5,60,10,30)
        assert '\x1b_Ga=T' in capsys.readouterr().out
        assert calls==[a]
        controller.frame_cleared();capsys.readouterr()
        controller.request(b,5,60,10,30)
        wait_for(lambda:controller._ready is not None)
        assert calls[-1]==b
        controller.paint_ready()
        import base64
        output=capsys.readouterr().out
        assert base64.b64encode(str(b).encode()).decode() in output
        assert base64.b64encode(str(a).encode()).decode() not in output
    finally:release.set()
