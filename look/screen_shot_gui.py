"""Numbered display picker; overlays vanish before full-resolution capture."""
import json
import sys
import tempfile
from pathlib import Path
from PySide6.QtCore import Qt,QTimer
from PySide6.QtGui import QColor,QFont,QPainter,QImage
from PySide6.QtWidgets import QApplication,QWidget
import screen_shot

SETTLE_MS=350


class Badge(QWidget):
    def __init__(self,controller,screen,index):
        super().__init__();self.controller=controller;self.index=index
        self.setWindowTitle('LOOK Shot')
        self.setWindowFlags(Qt.WindowType.Tool|Qt.WindowType.FramelessWindowHint|Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        area=screen.availableGeometry();self.setGeometry(area.x()+max(0,(area.width()-620)//2),area.y()+max(0,(area.height()-220)//2),min(620,area.width()),220)
    def paintEvent(self,event):
        painter=QPainter(self);painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setBrush(QColor('#19232e'));painter.setPen(QColor('#79a9de'));painter.drawRoundedRect(self.rect().adjusted(2,2,-2,-2),16,16)
        painter.setFont(QFont('Sans Serif',44,QFont.Weight.Bold))
        label=str(self.index+1)+(' ✓' if self.index in self.controller.selected else '')
        painter.drawText(self.rect().adjusted(15,12,-15,-100),Qt.AlignmentFlag.AlignCenter,label)
        painter.setPen(QColor('#e8e4da'));painter.setFont(QFont('Sans Serif',13))
        text=('Capture in '+str(self.controller.remaining) if self.controller.running else 'Numbers or click toggle · a all · Enter capture')+'\nEsc cancel · Multiple displays become one image'
        painter.drawText(self.rect().adjusted(10,110,-10,-10),Qt.AlignmentFlag.AlignCenter,text)
    def mousePressEvent(self,event):self.controller.toggle(self.index)
    def keyPressEvent(self,event):
        if event.key()==Qt.Key.Key_Escape:self.controller.cancel()
        elif event.key() in (Qt.Key.Key_Return,Qt.Key.Key_Enter):self.controller.start()
        elif event.text().lower()=='a' and not self.controller.running:self.controller.selected=set(range(len(self.controller.screens)));self.controller.redraw()
        elif event.text() in '123456789' and event.text():self.controller.toggle(int(event.text())-1)


class Controller:
    def __init__(self,app,options):
        self.app=app;self.options=options;self.screens=app.screens();self.selected=set();self.running=False;self.remaining=options['delay'];self.windows=[]
        if not self.screens:raise ValueError('No screens available in this desktop session')
        app.setQuitOnLastWindowClosed(False)
        app.screenAdded.connect(lambda _:self.changed());app.screenRemoved.connect(lambda _:self.changed())
        for index,screen in enumerate(self.screens):
            window=Badge(self,screen,index);self.windows.append(window);window.show()
        self.windows[0].raise_();self.windows[0].activateWindow()
        if options['screens']:
            self.selected=set(screen_shot.selection(options['screens'],len(self.screens)))
            QTimer.singleShot(0,self.start)
    def changed(self):
        print('Display configuration changed; run lk shot again.',flush=True);self.app.exit(1)
    def redraw(self):
        for window in self.windows:window.update()
    def toggle(self,index):
        if self.running or index>=len(self.screens):return
        if index in self.selected:self.selected.remove(index)
        else:self.selected.add(index)
        self.redraw()
    def cancel(self):print('Screenshot cancelled.',flush=True);self.app.exit(0)
    def start(self):
        if self.running or not self.selected:return
        self.running=True;self.tick()
    def tick(self):
        if self.remaining>0:
            self.redraw();QTimer.singleShot(1000,self.advance)
        else:
            for window in self.windows:window.hide()
            QTimer.singleShot(SETTLE_MS,self.capture)
    def advance(self):
        self.remaining-=1;self.tick()
    def capture(self):
        try:
            # Use this exact inventory for both labels and capture, avoiding
            # mismatched system_profiler versus OS display numbering.
            images=[]
            for index in sorted(self.selected):
                image=self.screens[index].grabWindow(0).toImage()
                if image.isNull():raise ValueError('Screen capture unavailable; allow Screen Recording for this terminal in system settings')
                image.setDevicePixelRatio(1);images.append(image)
            width=sum(image.width() for image in images);height=max(image.height() for image in images)
            if width*height>100_000_000:raise ValueError('Selected display image is too large; capture fewer displays')
            combined=QImage(width,height,QImage.Format.Format_RGB32);combined.fill(QColor('#000000'))
            painter=QPainter(combined);x=0
            for image in images:painter.drawImage(x,0,image);x+=image.width()
            painter.end()
            with tempfile.TemporaryDirectory(prefix='look-shot-') as folder:
                path=Path(folder)/'screen.png'
                if not combined.save(str(path),'PNG'):raise ValueError('Could not encode screenshot')
                if self.options['save']:
                    with Path(self.options['save']).open('xb') as out:out.write(path.read_bytes())
                screen_shot.copy_image(path)
            print('Screenshot copied · '+', '.join(str(i+1) for i in sorted(self.selected))+' · '+str(width)+' × '+str(height),flush=True)
            if self.options['save']:print('Saved '+self.options['save'],flush=True)
            self.app.exit(0)
        except Exception as exc:print('LOOK Shot: '+str(exc),flush=True);self.app.exit(1)


def main():
    options=json.loads(sys.stdin.read());app=QApplication(['LOOK Shot'])
    try:controller=Controller(app,options)
    except ValueError as exc:print(str(exc));return 1
    return app.exec()


if __name__=='__main__':raise SystemExit(main())
