import io
import os
from pathlib import Path
import struct
from concurrent.futures import Future

import pytest
import book_reader
import look_renderer
import media_offline


def test_reader_preferences_and_foreground_launch(tmp_path,monkeypatch):
    monkeypatch.setattr(Path,'home',lambda:tmp_path)
    monkeypatch.setattr(book_reader,'binary',lambda name:'/tools/bookokrat' if name=='bookokrat' else None)
    monkeypatch.setattr(book_reader,'graphics',lambda:True)
    path=tmp_path/'A Book.epub';path.write_bytes(b'book')
    assert book_reader.preference()=='auto'
    assert book_reader.command(path)==['/tools/bookokrat',str(path),'--zen-mode']
    calls=[]
    class Result:returncode=0
    monkeypatch.setattr(book_reader.subprocess,'run',lambda args,**kw:calls.append((args,kw)) or Result())
    result=book_reader.open_book(path,lambda path:pytest.fail('must remain in terminal'))
    assert 'Returned from Bookokrat' in result and calls[0][1]['cwd']==tmp_path/'.local/share/look/book-reader'
    assert 'stdin' not in calls[0][1] and 'start_new_session' not in calls[0][1]
    book_reader.preference('system')
    assert book_reader.open_book(path,lambda path:'OPEN OK · system')=='Opened in system reader'
    assert len(calls)==1


def test_pdf_needs_graphics_but_epub_can_be_text_only(tmp_path,monkeypatch):
    monkeypatch.setattr(book_reader,'binary',lambda name:'/tools/bookokrat')
    monkeypatch.setattr(book_reader,'graphics',lambda:False)
    assert book_reader.command(tmp_path/'book.epub',mode='bookokrat')[-1]=='--no-images'
    assert book_reader.command(tmp_path/'paper.pdf',mode='auto') is None
    with pytest.raises(ValueError,match='graphics-capable'):book_reader.command(tmp_path/'paper.pdf',mode='bookokrat')


def test_setup_is_confirmed_fixed_and_deduplicated(tmp_path,monkeypatch):
    monkeypatch.setattr(Path,'home',lambda:tmp_path)
    monkeypatch.setattr(book_reader,'binary',lambda name:'/tools/brew' if name=='brew' else None)
    calls=[];monkeypatch.setattr(book_reader.subprocess,'Popen',lambda args,**kw:calls.append((args,kw)))
    with pytest.raises(PermissionError):book_reader.install()
    first=book_reader.install(confirmed=True)
    second=book_reader.install(confirmed=True)
    assert first['setup']['job']==second['setup']['job'] and len(calls)==1
    assert calls[0][0][2]=='--install-worker' and calls[0][1]['start_new_session']
    assert 'sudo' not in calls[0][0]


def test_availability_timestamp_refresh_does_not_redraw_unchanged_rows():
    availability=media_offline.Availability({'local'})
    try:
        key=(('owner','id','/track'),)
        availability.checked[key]=(0,'remote')
        for state,changed in [('remote',False),('offline',True),('offline',False),('remote',True)]:
            future=Future();future.set_result(state);availability.pending[key]=future
            assert availability.poll([]) is changed
            assert availability.checked[key][1]==state
    finally:availability.close()


class Terminal(io.StringIO):
    def __init__(self):super().__init__();self.held=False;self.visual='native';self.presented=[]
    def write(self,text):
        # Model presentation at flush boundaries, including flushes made by the
        # native adapter between delete/text/image operations.
        if '\x1b[?2026h' in text:self.held=True
        if '\x1b_Ga=d' in text:self.visual='blank'
        if 'ASCII' in text:self.visual='ASCII'
        if '\x1b_Ga=T' in text:self.visual='native'
        if '\x1b[?2026l' in text:self.held=False
        return super().write(text)
    def flush(self):
        if not self.held:self.presented.append(self.visual)


def test_native_redraw_never_presents_intermediate_ascii(tmp_path,monkeypatch):
    monkeypatch.setenv('LOOK_NATIVE_PREVIEW','off')
    monkeypatch.setenv('KITTY_WINDOW_ID','test')
    controller=look_renderer.NativePreviewController();controller.enabled=True;controller.driver='kitty'
    image=tmp_path/'cover.png';image.write_bytes(b'\x89PNG\r\n\x1a\n'+b'\0\0\0\rIHDR'+struct.pack('>II',16,16))
    key=(str(image.resolve()),image.stat().st_mtime_ns,5,60,10,30)
    controller._prepared=(key,image)
    terminal=Terminal();monkeypatch.setattr(look_renderer.sys,'stdout',terminal)
    for _ in range(8):
        with look_renderer.synchronized_update():
            controller.frame_cleared()
            terminal.write('ASCII');terminal.flush()
            controller.request(image,5,60,10,30)
            controller.paint_ready()
    assert terminal.presented==['native']*8


def test_synchronized_frame_always_closes_on_exception(monkeypatch):
    monkeypatch.setenv('KITTY_WINDOW_ID','test')
    terminal=io.StringIO();monkeypatch.setattr(look_renderer.sys,'stdout',terminal)
    with pytest.raises(RuntimeError):
        with look_renderer.synchronized_update():
            with look_renderer.synchronized_update():raise RuntimeError('failed render')
    assert terminal.getvalue().count('\x1b[?2026h')==1
    assert terminal.getvalue().endswith('\x1b[?2026l')
