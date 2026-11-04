"""Flight Deck curtain desktop edge; normal desktop escape routes still exist."""
import concurrent.futures
import time
from PySide6.QtCore import Qt,QTimer
from PySide6.QtGui import QPainter,QColor
from PySide6.QtWidgets import QApplication,QInputDialog,QLineEdit
import curtain_client
import saver
import saver_gui


class CurtainWindow(saver_gui.SaverWindow):
    def paintEvent(self,event):
        super().paintEvent(event)
        painter=QPainter(self);painter.fillRect(12,12,min(570,self.width()-24),32,QColor('#101719'))
        painter.setPen(QColor('#e6e6cf'));painter.drawText(22,33,'LOOK CURTAIN · Enter/click: PIN · C colors · V visual');painter.end()
    def keyPressEvent(self,event):
        if event.isAutoRepeat():return
        if event.key() in {Qt.Key.Key_C,Qt.Key.Key_V}:super().keyPressEvent(event)
        else:self.controller.prompt()
    def mousePressEvent(self,event):self.controller.prompt()
    def closeEvent(self,event):
        if self.removing:event.accept()
        else:event.ignore();self.controller.prompt()


class CurtainController(saver_gui.SaverController):
    def __init__(self,app):
        self.dialog=None;self.pending=None
        self.executor=concurrent.futures.ThreadPoolExecutor(max_workers=1)
        settings=saver.curtain_settings()
        super().__init__(app,settings)
        self.poll_timer=QTimer(app);self.poll_timer.timeout.connect(self.poll);self.poll_timer.start(500)
        self.poll()
    def prompt(self):
        if self.dialog is not None:return
        parent=next(iter(self.windows.values()),None)
        dialog=QInputDialog(parent);self.dialog=dialog
        dialog.setWindowTitle('LOOK Curtain');dialog.setLabelText('Four-digit PIN · ambient curtain, not an OS lock')
        dialog.setTextEchoMode(QLineEdit.EchoMode.Password)
        dialog.textValueChanged.connect(lambda text:dialog.accept() if len(text)==4 and text.isascii() and text.isdigit() else None)
        dialog.accepted.connect(lambda:self.unlock(dialog.textValue()))
        dialog.finished.connect(lambda *_:setattr(self,'dialog',None))
        dialog.open()
    def unlock(self,pin):
        if self.pending is not None and not self.pending.done():
            self.queued_pin=pin;return
        self.pending=self.executor.submit(curtain_client.request,'unlock',pin=pin)
    def poll(self):
        if self.pending is not None:
            if not self.pending.done():return
            try:
                state=self.pending.result()
                captions=tuple(state.get('captions',[]))
                for window in self.windows.values():window.run.captions=captions
                if not state.get('locked',True):self.dismiss();return
            except Exception as exc:
                # Keep the curtain visible if the local node is unavailable.
                if self.dialog:self.dialog.setLabelText(str(exc))
                else:
                    self.prompt()
                    self.dialog.setLabelText(str(exc))
            self.pending=None
        if hasattr(self,'queued_pin'):
            pin=self.queued_pin;del self.queued_pin;self.unlock(pin)
        else:self.pending=self.executor.submit(curtain_client.request)
    def dismiss(self):
        if hasattr(self,'poll_timer'):self.poll_timer.stop()
        self.executor.shutdown(wait=False,cancel_futures=True)
        super().dismiss()


def main():
    saver_gui.HINT_SECONDS=0
    saver_gui.SaverWindow=CurtainWindow
    app=QApplication(['LOOK Curtain'])
    controller=CurtainController(app)
    try:return app.exec()
    finally:
        controller.dismiss()


if __name__=='__main__':raise SystemExit(main())
