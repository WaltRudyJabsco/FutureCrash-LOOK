"""Flight Deck curtain desktop edge; normal desktop escape routes still exist."""
import concurrent.futures
import time
import random
from functools import lru_cache
from PySide6.QtCore import Qt,QTimer,QRect
from PySide6.QtGui import QPainter,QColor,QFont,QFontMetricsF
from PySide6.QtWidgets import QApplication,QInputDialog,QLineEdit
import curtain_client
import saver
import saver_gui


THEY_LIVE_WORDS=('OBEY','CONSUME','REPRODUCE','SLEEP','CONFORM','SUBMIT','STAY ASLEEP','DO NOT QUESTION')
THEY_LIVE_SECONDS=12

@lru_cache(maxsize=32)
def phrase_order(seed):
    words=list(THEY_LIVE_WORDS);random.Random(seed).shuffle(words)
    return tuple(words)

def they_live_word(now,epoch,slot=0,seed=0):
    words=phrase_order(seed)
    step=int(max(0,now-epoch)//THEY_LIVE_SECONDS)
    return words[(step+slot)%len(words)]

CRT_SECONDS=.65

def crt_shape(progress):
    progress=max(0,min(1,progress))
    if progress<.65:return 1,max(.004,(1-progress/.65)**2)
    return max(0,(1-(progress-.65)/.35)**2),.004


class CurtainWindow(saver_gui.SaverWindow):
    def paintEvent(self,event):
        if self.controller.shutdown_started is not None:
            progress=(time.monotonic()-self.controller.shutdown_started)/CRT_SECONDS
            width,height=crt_shape(progress)
            painter=QPainter(self);painter.fillRect(self.rect(),QColor('black'))
            target=QRect(int(self.width()*(1-width)/2),int(self.height()*(1-height)/2),max(1,int(self.width()*width)),max(1,int(self.height()*height)))
            if progress<.65:painter.drawPixmap(target,self.shutdown_image)
            elif progress<1:painter.fillRect(target,QColor('white'))
            painter.end();return
        if self.controller.variant=='they-live':
            painter=QPainter(self);painter.fillRect(self.rect(),QColor('white'));painter.setPen(QColor('black'))
            text=they_live_word(time.time(),self.controller.variant_epoch,getattr(self,'museum_slot',0),self.controller.phrase_seed)
            font=QFont('Arial');font.setWeight(QFont.Weight.Black);font.setPixelSize(100)
            metrics=QFontMetricsF(font)
            scale=min(self.width()*.88/max(1,metrics.horizontalAdvance(text)),self.height()*.65/metrics.height())
            font.setPixelSize(max(1,int(100*scale)));painter.setFont(font)
            painter.drawText(self.rect(),Qt.AlignmentFlag.AlignCenter,text);painter.end();return
        super().paintEvent(event)
        painter=QPainter(self);painter.fillRect(12,12,min(570,self.width()-24),32,QColor('#101719'))
        painter.setPen(QColor('#e6e6cf'));painter.drawText(22,33,'LOOK CURTAIN · Enter/click: PIN · C colors · V visual');painter.end()
    def keyPressEvent(self,event):
        if event.isAutoRepeat():return
        if self.controller.variant!='they-live' and event.key() in {Qt.Key.Key_C,Qt.Key.Key_V}:super().keyPressEvent(event)
        else:self.controller.prompt()
    def mousePressEvent(self,event):self.controller.prompt()
    def closeEvent(self,event):
        if self.removing:event.accept()
        else:event.ignore();self.controller.prompt()


class CurtainController(saver_gui.SaverController):
    def __init__(self,app):
        self.dialog=None;self.pending=None;self.variant='standard';self.variant_epoch=0;self.phrase_seed=random.SystemRandom().getrandbits(64);self.shutdown_started=None
        self.executor=concurrent.futures.ThreadPoolExecutor(max_workers=1)
        settings=saver.curtain_settings()
        super().__init__(app,settings)
        self.poll_timer=QTimer(app);self.poll_timer.timeout.connect(self.poll);self.poll_timer.start(500)
        self.poll()
    def prompt(self):
        if self.shutdown_started is not None:return
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
        if self.shutdown_started is not None:return
        if self.pending is not None:
            if not self.pending.done():return
            try:
                state=self.pending.result()
                self.variant=state.get('variant','standard');self.variant_epoch=state.get('revision',0)/1e9
                captions=tuple(state.get('captions',[]))
                for window in self.windows.values():window.run.captions=captions
                if not state.get('locked',True):self.finish_unlock();return
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
    def finish_unlock(self):
        if self.variant!='they-live':self.dismiss();return
        if self.shutdown_started is not None:return
        if self.dialog:self.dialog.hide()
        for window in self.windows.values():window.shutdown_image=window.grab()
        self.shutdown_started=time.monotonic()
        self.poll_timer.stop()
        QTimer.singleShot(round(CRT_SECONDS*1000),self.dismiss)

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
