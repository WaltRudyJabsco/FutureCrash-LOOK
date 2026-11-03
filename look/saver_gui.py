"""Qt display edge for LOOK Saver; no audio, network, or lock-screen ownership."""
from __future__ import annotations
import hashlib
import json
import random
import signal
import sys
import time

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QColor, QCursor, QFont, QFontDatabase, QFontMetricsF, QPainter
from PySide6.QtWidgets import QApplication, QWidget

import saver

FRAME_INTERVAL_MS=50
HINT_SECONDS=4
MAX_COLUMNS=240
MAX_ROWS=80


class SaverWindow(QWidget):
    def __init__(self,controller,screen,seed):
        super().__init__()
        self.controller=controller;self.removing=False
        self.run=saver.SceneRun(controller.settings,seed)
        self.font_family=next((name for name in ('Menlo','DejaVu Sans Mono','Liberation Mono','Courier New') if name in QFontDatabase.families()),QFontDatabase.systemFont(QFontDatabase.SystemFont.FixedFont).family())
        self.layout_size=None
        self.setWindowTitle('LOOK Saver Preview' if controller.preview else 'LOOK Saver')
        if not controller.preview:
            self.setWindowFlags(Qt.WindowType.Window | Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
            self.setCursor(Qt.CursorShape.BlankCursor)
        self.setScreen(screen)
        self.setAttribute(Qt.WidgetAttribute.WA_OpaquePaintEvent)
        if controller.preview:
            self.resize(900,540)
            self.move(screen.availableGeometry().center()-self.rect().center())
            self.show()
        else:
            self.setGeometry(screen.geometry())
            self.showFullScreen()
        screen.geometryChanged.connect(self.geometry_changed)

    def geometry_changed(self,geometry):
        if not self.controller.preview:self.setGeometry(geometry)

    def paintEvent(self,event):
        painter=QPainter(self)
        size=(self.width(),self.height())
        if size!=self.layout_size:
            self.font=QFont(self.font_family)
            self.font.setStyleHint(QFont.StyleHint.Monospace);self.font.setFixedPitch(True)
            self.font.setPixelSize(max(14,round(self.height()/65)))
            self.metrics=QFontMetricsF(self.font);self.layout_size=size
        painter.setFont(self.font)
        metrics=self.metrics
        cell_width=max(1,metrics.horizontalAdvance('M'));cell_height=max(1,metrics.height())
        columns=max(1,min(MAX_COLUMNS,int(self.width()/cell_width)))
        rows=max(1,min(MAX_ROWS,int(self.height()/cell_height)))
        elapsed=max(0,time.monotonic()-self.controller.started)
        _scene,lines,(paper,ink)=self.run.sample(elapsed,columns,rows)
        painter.fillRect(self.rect(),QColor(paper));painter.setPen(QColor(ink))
        left=(self.width()-columns*cell_width)/2
        top=(self.height()-rows*cell_height)/2+metrics.ascent()
        for index,line in enumerate(lines):painter.drawText(round(left),round(top+index*cell_height),line)
        if elapsed<HINT_SECONDS:
            painter.fillRect(12,12,260,30,QColor(paper))
            painter.drawText(22,33,'Escape · return to terminal')
        painter.end()

    def keyPressEvent(self,event):
        if event.key() in {Qt.Key.Key_Escape,Qt.Key.Key_Q}:self.controller.app.quit()
        else:event.ignore()

    def mousePressEvent(self,event):self.controller.app.quit()

    def closeEvent(self,event):
        if not self.removing:self.controller.app.quit()
        event.accept()


class SaverController:
    def __init__(self,app,settings,*,preview=False,seconds=None,seed=None):
        self.app=app;self.settings=saver.validate(settings);self.preview=preview
        self.started=time.monotonic();self.windows={}
        self.seed=random.SystemRandom().randrange(2**63) if seed is None else seed
        self.current=app.screenAt(QCursor.pos()) or app.primaryScreen()
        app.setQuitOnLastWindowClosed(False)
        self.reconcile()
        app.screenAdded.connect(lambda screen:self.reconcile())
        app.screenRemoved.connect(lambda screen:self.reconcile(exclude=screen))
        self.timer=QTimer(app);self.timer.timeout.connect(self.tick);self.timer.start(FRAME_INTERVAL_MS)
        if seconds is not None:QTimer.singleShot(round(seconds*1000),app.quit)

    def targets(self,exclude=None):
        screens=[screen for screen in self.app.screens() if screen is not exclude]
        if not screens:return []
        if self.preview or self.settings['display']=='current':
            return [self.current if self.current in screens else screens[0]]
        return screens

    def reconcile(self,exclude=None):
        targets=self.targets(exclude)
        for screen in list(self.windows):
            if screen not in targets:
                window=self.windows.pop(screen);window.removing=True;window.close();window.deleteLater()
        for index,screen in enumerate(targets):
            if screen not in self.windows:
                identity=f'{screen.name()}:{screen.serialNumber()}:{index}'
                offset=int.from_bytes(hashlib.sha256(identity.encode()).digest()[:8],'big') if self.settings['independent'] else 0
                self.windows[screen]=SaverWindow(self,screen,self.seed+offset)
        if not targets:self.app.quit()

    def tick(self):
        for window in self.windows.values():window.update()


def main():
    try:
        raw=sys.stdin.read(saver.MAX_SETTINGS_BYTES+1)
        if len(raw)>saver.MAX_SETTINGS_BYTES:raise ValueError('Saver request too large')
        payload=json.loads(raw);settings=saver.validate(payload['settings'])
        # Fail before creating windows when a malformed/empty cycle is requested.
        saver.SceneRun(settings,0)
        seconds=payload.get('seconds')
        if seconds is not None and (not isinstance(seconds,(int,float)) or not 0<seconds<=86400):raise ValueError('Invalid duration')
    except (KeyError,TypeError,ValueError) as exc:
        print('LOOK SAVER · '+str(exc),file=sys.stderr);return 1
    app=QApplication(['LOOK Saver']);app.setApplicationName('LOOK Saver')
    controller=SaverController(app,settings,preview=bool(payload.get('preview')),seconds=seconds)
    previous=signal.signal(signal.SIGINT,lambda *_:app.quit())
    try:return app.exec()
    finally:
        controller.timer.stop()
        signal.signal(signal.SIGINT,previous)
        for window in controller.windows.values():window.removing=True;window.close()


if __name__=='__main__':raise SystemExit(main())
