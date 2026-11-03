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


class MacPresentation:
    """App-local Cocoa presentation; never writes global menu/Dock preferences."""
    HIDE_DOCK=1 << 1
    HIDE_MENU_BAR=1 << 3

    def __init__(self):
        import ctypes
        self.objc=ctypes.CDLL('/usr/lib/libobjc.A.dylib')
        self.objc.objc_getClass.argtypes=[ctypes.c_char_p]
        self.objc.objc_getClass.restype=ctypes.c_void_p
        self.objc.sel_registerName.argtypes=[ctypes.c_char_p]
        self.objc.sel_registerName.restype=ctypes.c_void_p
        pointer=ctypes.c_void_p;uint=ctypes.c_ulong
        self.object_message=ctypes.CFUNCTYPE(pointer,pointer,pointer)(('objc_msgSend',self.objc))
        self.get_options=ctypes.CFUNCTYPE(uint,pointer,pointer)(('objc_msgSend',self.objc))
        self.set_options=ctypes.CFUNCTYPE(None,pointer,pointer,uint)(('objc_msgSend',self.objc))
        self.application=self.object_message(self.objc.objc_getClass(b'NSApplication'),self.selector('sharedApplication'))
        if not self.application:raise RuntimeError('macOS saver presentation is unavailable')
        self.original=None

    def selector(self,name):return self.objc.sel_registerName(name.encode('ascii'))

    def enter(self):
        if self.original is None:self.original=self.get_options(self.application,self.selector('presentationOptions'))
        # Cocoa requires hideDock together with hideMenuBar. These options keep
        # Escape and app switching available; this is not a kiosk or screen lock.
        self.set_options(self.application,self.selector('setPresentationOptions:'),self.HIDE_DOCK | self.HIDE_MENU_BAR)

    def restore(self):
        if self.original is not None:
            self.set_options(self.application,self.selector('setPresentationOptions:'),self.original)
            self.original=None


class SaverWindow(QWidget):
    def __init__(self,controller,screen,seed):
        super().__init__()
        self.controller=controller;self.removing=False
        self.run=saver.SceneRun(controller.settings,seed)
        if not controller.settings['independent'] and controller.windows:
            self.run.copy_controls_from(next(iter(controller.windows.values())).run)
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
            if controller.presentation is not None:
                # Native Cocoa fullscreen creates Spaces and transient toolbar
                # chrome. Borderless display windows avoid that transition.
                self.show()
            else:self.showFullScreen()
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
        for index,line in enumerate(lines):
            inverse=index in self.run.inverse_rows
            if inverse:painter.fillRect(0,round(top-metrics.ascent()+index*cell_height),self.width(),round(cell_height+1),QColor(ink))
            painter.setPen(QColor(paper if inverse else ink))
            painter.drawText(round(left),round(top+index*cell_height),line)
        painter.setPen(QColor(ink))
        if elapsed<HINT_SECONDS:
            hint='C colors · V visual · Space/Escape exit'
            painter.fillRect(12,12,round(metrics.horizontalAdvance(hint))+20,30,QColor(paper))
            painter.drawText(22,33,hint)
        painter.end()

    def keyPressEvent(self,event):
        # One physical press changes one scene/color; held keys cannot race
        # through colors or accidentally turn into a flashing animation.
        if event.isAutoRepeat():return
        if event.key()==Qt.Key.Key_C:self.controller.change_visual(color=True)
        elif event.key()==Qt.Key.Key_V:self.controller.change_visual(color=False)
        elif event.key() in {Qt.Key.Key_Escape,Qt.Key.Key_Space}:self.controller.dismiss()
        else:event.ignore()

    def mousePressEvent(self,event):self.controller.dismiss()

    def closeEvent(self,event):
        if not self.removing:self.controller.dismiss()
        event.accept()


class SaverController:
    def __init__(self,app,settings,*,preview=False,seconds=None,seed=None):
        self.app=app;self.settings=saver.validate(settings);self.preview=preview
        self.started=time.monotonic();self.windows={};self.stopping=False
        self.presentation=MacPresentation() if not preview and app.platformName()=='cocoa' else None
        if self.presentation is not None:
            self.presentation.enter()
            app.aboutToQuit.connect(self.presentation.restore)
            app.applicationStateChanged.connect(self.presentation_changed)
        self.seed=random.SystemRandom().randrange(2**63) if seed is None else seed
        self.current=app.screenAt(QCursor.pos()) or app.primaryScreen()
        app.setQuitOnLastWindowClosed(False)
        self.reconcile()
        app.screenAdded.connect(lambda screen:self.reconcile())
        app.screenRemoved.connect(lambda screen:self.reconcile(exclude=screen))
        self.timer=QTimer(app);self.timer.timeout.connect(self.tick);self.timer.start(FRAME_INTERVAL_MS)
        if seconds is not None:QTimer.singleShot(round(seconds*1000),self.dismiss)

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
        if not targets:self.dismiss()
        elif self.presentation is not None:
            focused=self.windows.get(self.current) or next(iter(self.windows.values()))
            focused.raise_();focused.activateWindow()
            QTimer.singleShot(0,self.settle_presentation)

    def settle_presentation(self):
        if self.stopping:return
        self.presentation.enter()
        # AppKit may constrain initial windows to the old visible desktop before
        # presentation options take effect. Reapply each full display rectangle.
        for screen,window in self.windows.items():window.setGeometry(screen.geometry())

    def presentation_changed(self,state):
        if state==Qt.ApplicationState.ApplicationActive:self.settle_presentation()

    def dismiss(self):
        if self.stopping:return
        self.stopping=True
        if self.presentation is not None:self.presentation.restore()
        if hasattr(self,'timer'):self.timer.stop()
        for window in self.windows.values():window.removing=True;window.close()
        self.app.quit()

    def change_visual(self,*,color):
        for window in self.windows.values():
            if color:window.run.next_color()
            else:window.run.next_scene(elapsed=max(0,time.monotonic()-self.started))
            window.update()

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
    previous=signal.signal(signal.SIGINT,lambda *_:controller.dismiss())
    try:return app.exec()
    finally:
        controller.timer.stop()
        if controller.presentation is not None:controller.presentation.restore()
        signal.signal(signal.SIGINT,previous)
        for window in controller.windows.values():window.removing=True;window.close()


if __name__=='__main__':raise SystemExit(main())
