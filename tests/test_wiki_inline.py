from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock
import os
import re
import struct
import threading
import pytest
import wiki
import wiki_inline
import look_renderer
import books
from test_media_request_regressions import lk


def article():
    return wiki.article_payload('<p>Before <a href="Intro">intro</a>.</p><figure><a href="./File:Photo.jpg"><img src="//thumb.wikimedia.org/wikipedia/commons/thumb/a/ab/Photo.jpg/300px-Photo.jpg" width="300" height="180" alt="Photo"></a><figcaption>Caption</figcaption></figure><p>After <a href="After">after</a>.</p>','Example','Example',live=True)


def test_images_keep_article_position_and_fixed_layout_before_loading():
    value=article();ui=SimpleNamespace(_c=lambda text,style:text)
    assert value['images'][0]['before']==1
    assert [''.join(r['text'] for r in rows) for rows in value['rich_paragraphs']]==value['paragraphs']
    lines,anchors,blocks=wiki_inline.layout(ui,value,70,20)
    assert len(blocks)==1 and anchors==sorted(anchors)
    block=blocks[0]
    assert next(i for i,line in enumerate(lines) if 'Before' in line)<block['start']
    assert next(i for i,line in enumerate(lines) if 'After' in line)>block['start']+block['rows']
    plain,_,hidden=wiki_inline.layout(ui,value,70,20,show=False)
    assert hidden==[] and not any(line.startswith('IMAGE') for line in plain)


def test_inline_work_only_requests_visible_images_and_slices_partial_ascii(monkeypatch,lk,tmp_path):
    value=article();lines,anchors,blocks=wiki_inline.layout(lk,value,70,20)
    block=blocks[0];height=block['rows']
    work=Mock();work.get.return_value=([str(i) for i in range(height)],None,'')
    factory=Mock(return_value=work);monkeypatch.setattr(wiki_inline,'LatestWork',factory)
    painter=wiki_inline.InlineImages(lk,live=True);painter.reset(value)
    try:
        painter.compose(lines,blocks,block['start']+height+2,4)
        factory.assert_not_called()
        visible=painter.compose(lines,blocks,block['start']+2,3,native_images=False)
        assert [v.strip() for v in visible]==['2','3','4']
        assert painter.pending==[]
        assert len(lines)==len(anchors)  # Image readiness never changes document rows.
    finally:painter.close()
    work.close.assert_called_once()


def png(path,w=160,h=160):
    path.write_bytes(b'\x89PNG\r\n\x1a\n'+b'\0\0\0\rIHDR'+struct.pack('>II',w,h));return path


def test_native_crop_never_paints_over_header_or_footer(tmp_path,monkeypatch,capsys):
    monkeypatch.setenv('LOOK_NATIVE_PREVIEW','off')
    monkeypatch.setattr(look_renderer.NativePreviewController,'_cell_pixels',staticmethod(lambda:(8,16)))
    image=png(tmp_path/'image.png')
    controller=look_renderer.NativePreviewController();controller.driver='kitty';controller.clip_rows=(2,8)
    controller._ready=(controller._generation,image,-3,1,10,20)
    controller.paint_ready();text=capsys.readouterr().out
    assert 'x=0,y=80,w=160,h=80,' in text and 'r=5,' in text
    rows=[int(row) for row in re.findall(r'\x1b\[(\d+);\d+H',text)]
    assert rows and all(2<=row<8 for row in rows)
    controller.driver='iterm';controller._ready=(controller._generation,image,-3,1,10,20)
    controller.paint_ready();assert capsys.readouterr().out==''
    controller.close()


def test_closed_native_worker_exits_and_cannot_paint_late_result(tmp_path,monkeypatch,capsys):
    monkeypatch.setenv('KITTY_WINDOW_ID','123');monkeypatch.setenv('LOOK_NATIVE_PREVIEW','on')
    entered=threading.Event();release=threading.Event()
    image=png(tmp_path/'image.png')
    def prepare(self,*args):entered.set();release.wait(2);return image
    monkeypatch.setattr(look_renderer.NativePreviewController,'_prepare',prepare)
    controller=look_renderer.NativePreviewController()
    controller.request(image,3,1,10,20);assert entered.wait(1)
    controller.close();release.set();controller._thread.join(1)
    assert not controller._thread.is_alive() and controller.wakeup_fd is None
    controller.paint_ready();assert capsys.readouterr().out==''


def terminal(monkeypatch):
    import termios,tty
    class Terminal:
        def fileno(self):return 0
        def isatty(self):return True
    monkeypatch.setattr(wiki.sys,'stdin',Terminal())
    monkeypatch.setattr(termios,'tcgetattr',lambda fd:[])
    monkeypatch.setattr(termios,'tcsetattr',lambda *a:None)
    monkeypatch.setattr(tty,'setcbreak',lambda fd:None)


def test_wiki_panes_from_shelf_article_and_link_picker_keep_place(lk,monkeypatch,capsys):
    terminal(monkeypatch)
    pane=Mock(return_value='Shell opened beside LOOK · Option-Shift-W switch pane · Ctrl-Shift-W close focused pane')
    monkeypatch.setattr(wiki.terminal_style,'open_pane',pane)
    value={'title':'Article','path':'Article','paragraphs':['A link'],'links':[{'title':'Other','path':'Other'}]}
    monkeypatch.setattr(wiki,'request',lambda action='status',**k:value if action=='article' else {'root':'/ref','archives':[{'id':'test.zim','title':'Saved'}],'jobs':[],'reader_installed':True})
    keys=iter(['W','down','enter','W','l','W','esc','esc','esc'])
    monkeypatch.setattr(lk,'_read_tty_key',lambda *args:next(keys))
    assert wiki.desk(lk,'owner')==0
    assert pane.call_count==3 and all(call.args==(Path.cwd(),) for call in pane.call_args_list)
    assert 'close focused pane' in capsys.readouterr().out


def test_books_pane_status_is_complete_and_search_uppercase_w_stays_text(lk,monkeypatch,capsys):
    terminal(monkeypatch)
    monkeypatch.setattr(books,'catalog',lambda:{'entries':[]})
    pane=Mock(return_value='Shell opened beside LOOK · Option-Shift-W switch pane · Ctrl-Shift-W close focused pane')
    monkeypatch.setattr(books.terminal_style,'open_pane',pane)
    keys=iter(['W','/','W','esc','esc','esc'])
    monkeypatch.setattr(lk,'_read_tty_key',lambda *args:next(keys))
    assert books.desk(lk,owner='local')==0
    pane.assert_called_once_with(Path.cwd())
    text=lk._strip_ansi(capsys.readouterr().out)
    assert 'Shell opened beside LOOK' in text and 'close focused pane' in text and 'FILTER W' in text


def test_inline_hints_and_resize_keep_source_anchor():
    from test_wiki_reading_anchor import long_article
    value=long_article()
    value['images']=[dict(article()['images'][0],before=0)]
    ui=SimpleNamespace(_c=lambda text,style:text)
    normal,anchors,blocks=wiki_inline.layout(ui,value,70,20)
    target=next(i for i,line in enumerate(normal) if 'Muslim' in line)
    position=anchors[target]
    for width in (40,70,110):
        hinted,marked,_=wiki_inline.layout(ui,value,width,20,hints=True)
        top=wiki.anchored_top(marked,position,6)
        assert any('Muslim' in line for line in hinted[top+6:top+8])
    assert wiki.anchored_top(anchors,position,6)==target-6


def test_article_image_toggles_and_idle_do_not_repaint(lk,monkeypatch):
    terminal(monkeypatch)
    value=article();frames=[]
    monkeypatch.setattr(wiki,'request',lambda action='status',**k:value if action=='article' else {'archives':[{'id':'test.zim','title':'Saved'}]})
    monkeypatch.setattr(lk,'_terminal_frame_payload',lambda text:frames.append(lk._strip_ansi(text)) or '')
    work=Mock();work.get.return_value=(['ASCII PHOTO'],None,'')
    monkeypatch.setattr(wiki_inline,'LatestWork',lambda:work)
    clear=Mock();monkeypatch.setattr(wiki_inline.InlineImages,'clear',clear)
    keys=iter(['','','M','I','I','esc'])
    def read(*args):
        key=next(keys)
        if key=='M':assert clear.call_count==2  # Idle polls never redraw the article.
        return key
    monkeypatch.setattr(lk,'_read_tty_key',read)
    assert wiki.desk(lk,'owner',reference={'title':'Example','archive':'test.zim'})==0
    assert any('IMAGE 1' in text for text in frames)
    assert any('IMAGE 1' not in text for text in frames)
    assert work.close.call_count==1


def test_inline_clear_only_erases_native_placements_once(lk):
    painter=wiki_inline.InlineImages(lk)
    first=Mock(enabled=True);second=Mock(enabled=True)
    painter.native={0:first,1:second}
    painter.clear()
    first.frame_cleared.assert_called_once()
    second.frame_cleared.assert_not_called()
    second.invalidate.assert_called_once()
    painter.close()
    first.close.assert_called_once();second.close.assert_called_once()
