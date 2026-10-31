from types import SimpleNamespace
import os
import pytest
import wiki
from test_media_request_regressions import lk


def long_article():
    html='<p>'+''.join('The history of <a href="Topic_'+str(i)+'">Alexandria '+str(i)+'</a> includes trade and culture. ' for i in range(90))
    html+='<a href="Muslim_conquest_of_Egypt">Muslim conquest of Egypt</a> changed the city. '+('Later history continues. '*40)+'</p>'
    return wiki.article_payload(html,'Alexandria','Alexandria')


@pytest.mark.parametrize('width',[40,70,110])
def test_hint_layout_keeps_center_text_and_roundtrips_without_drift(width):
    ui=SimpleNamespace(_c=lambda text,style:text);article=long_article()
    normal=[];plain=wiki.article_lines(ui,article,width,anchors=normal)
    marked=[];hinted=wiki.article_lines(ui,article,width,True,marked)
    assert normal==sorted(normal) and marked==sorted(marked)
    target=next(i for i,line in enumerate(plain) if 'Muslim' in line)
    row=6;top=target-row;position=normal[target]
    new_top=wiki.anchored_top(marked,position,row)
    # The words in the original center line remain within one rewrapped line.
    assert any('Muslim' in line for line in hinted[new_top+row:new_top+row+2])
    assert new_top>top  # Confirms this fixture reproduces expansion above the viewport.
    for _ in range(10):
        assert wiki.anchored_top(normal,position,row)==top
        assert wiki.anchored_top(marked,position,row)==new_top


def test_mid_article_hint_toggle_preserves_frame_and_footer_height(lk,monkeypatch,capsys):
    import termios,tty
    class Terminal:
        def fileno(self):return 0
        def isatty(self):return True
    monkeypatch.setattr(wiki.sys,'stdin',Terminal())
    monkeypatch.setattr(termios,'tcgetattr',lambda fd:[])
    monkeypatch.setattr(termios,'tcsetattr',lambda *a:None)
    monkeypatch.setattr(tty,'setcbreak',lambda fd:None)
    monkeypatch.setattr(lk.shutil,'get_terminal_size',lambda *a:os.terminal_size((70,26)))
    article=long_article()
    def request(action='status',**kw):
        if action=='article':return article
        return {'root':'/reference','archives':[{'id':'test.zim','title':'Saved Wikipedia'}],'jobs':[],'reader_installed':True}
    monkeypatch.setattr(wiki,'request',request)
    frames=[];before=[]
    monkeypatch.setattr(lk,'_terminal_frame_payload',lambda text:frames.append(lk._strip_ansi(text)) or '')
    keys=iter(['down','enter',*(['shiftdown']*5),'f','esc','f','esc','esc','esc'])
    def read(*args):
        key=next(keys)
        if key=='f':before.append(frames[-1])
        return key
    monkeypatch.setattr(lk,'_read_tty_key',read)
    assert wiki.desk(lk,'owner')==0
    assert before[0]==before[1]
    article_frames=[f for f in frames if 'SAVED ARCHIVE' in f]
    assert len({len(f.split('\n')) for f in article_frames})==1
    assert any('LINK HINTS' in f for f in article_frames)
