from pathlib import Path
import time
from PySide6.QtWidgets import QApplication,QInputDialog,QMessageBox
from PySide6.QtCore import Qt,QEvent
from PySide6.QtGui import QImage,QKeyEvent
import museum_fullscreen,museum_desk,printing


def test_fullscreen_image_navigation_and_favorite(tmp_path,monkeypatch):
    app=QApplication.instance() or QApplication([])
    image=QImage(40,40,QImage.Format.Format_RGB32);image.fill(Qt.GlobalColor.blue)
    path=tmp_path/'image.png';image.save(str(path));calls=[]
    rows=[{'id':'aic-1','title':'One','downloaded':True},{'id':'aic-2','title':'Two','downloaded':True}]
    monkeypatch.setattr(museum_desk.Client,'image',lambda *args:path)
    def change(self,action,**fields):
        calls.append((action,fields));return {'items':[dict(row,favorite=row['id']==fields['id']) for row in rows]}
    monkeypatch.setattr(museum_desk.Client,'change',change)
    print_calls=[]
    monkeypatch.setattr(printing,'destinations',lambda:{'printers':[{'id':'receipt','label':'Little Printer','routes':[{'profile':{'kind':'escpos'}}]}]})
    def prepare(ident,image):
        print_calls.append(('prepare',ident,image));return {'id':'a'*32,'node':'archive','destination':'Little Printer','estimated_paper_mm':61}
    monkeypatch.setattr(printing,'prepare_file',prepare)
    monkeypatch.setattr(printing,'request',lambda action,node,**fields:print_calls.append((action,node,fields)) or {'state':'queued'})
    def pick(*args):
        # A modal dialog processes timers; the completed future must be consumed.
        args[0].poll()
        return 'Little Printer',True
    monkeypatch.setattr(QInputDialog,'getItem',pick)
    monkeypatch.setattr(QMessageBox,'question',lambda *args:QMessageBox.StandardButton.Yes)

    def run(self):
        window=next(w for w in self.topLevelWidgets() if w.windowTitle()=='LOOK Museum')
        def wait():
            deadline=time.monotonic()+2
            while window.future and time.monotonic()<deadline:window.poll();self.processEvents();time.sleep(.01)
            assert window.future is None
        wait();assert window.isFullScreen() and window.image is not None
        window.keyPressEvent(QKeyEvent(QEvent.Type.KeyPress,Qt.Key.Key_Right,Qt.KeyboardModifier.NoModifier))
        wait();assert window.index==1
        window.keyPressEvent(QKeyEvent(QEvent.Type.KeyPress,Qt.Key.Key_F,Qt.KeyboardModifier.NoModifier,'f'))
        wait();assert calls==[('favorite',{'id':'aic-2'})]
        window.keyPressEvent(QKeyEvent(QEvent.Type.KeyPress,Qt.Key.Key_F,Qt.KeyboardModifier.ShiftModifier,'F'))
        assert not window.isFullScreen()
        window.keyPressEvent(QKeyEvent(QEvent.Type.KeyPress,Qt.Key.Key_K,Qt.KeyboardModifier.NoModifier,'k'))
        wait();assert calls[-1]==('pin',{'id':'aic-2'})
        window.keyPressEvent(QKeyEvent(QEvent.Type.KeyPress,Qt.Key.Key_P,Qt.KeyboardModifier.NoModifier,'p'))
        wait();assert print_calls[0]==('prepare','receipt',path)
        assert print_calls[1]==('send','archive',{'ident':'a'*32,'confirm':True})
        assert len(print_calls)==2

        window.close();return 0
    monkeypatch.setattr(QApplication,'exec',run)
    # Reuse the test's QApplication rather than creating a second one.
    # main uses instance() when a GUI host already exists.
    assert museum_fullscreen.main({'owner':'local','rows':rows,'index':0,'playing':False})==0
