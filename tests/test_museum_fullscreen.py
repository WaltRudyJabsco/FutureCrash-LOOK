from pathlib import Path
import time
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt,QEvent
from PySide6.QtGui import QImage,QKeyEvent
import museum_fullscreen,museum_desk


def test_fullscreen_image_navigation_and_favorite(tmp_path,monkeypatch):
    app=QApplication.instance() or QApplication([])
    image=QImage(40,40,QImage.Format.Format_RGB32);image.fill(Qt.GlobalColor.blue)
    path=tmp_path/'image.png';image.save(str(path));calls=[]
    rows=[{'id':'aic-1','title':'One','downloaded':True},{'id':'aic-2','title':'Two','downloaded':True}]
    monkeypatch.setattr(museum_desk.Client,'image',lambda *args:path)
    def change(self,action,**fields):
        calls.append((action,fields));return {'items':[dict(row,favorite=row['id']==fields['id']) for row in rows]}
    monkeypatch.setattr(museum_desk.Client,'change',change)
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
        window.close();return 0
    monkeypatch.setattr(QApplication,'exec',run)
    # Reuse the test's QApplication rather than creating a second one.
    # main uses instance() when a GUI host already exists.
    assert museum_fullscreen.main({'owner':'local','rows':rows,'index':0,'playing':False})==0
