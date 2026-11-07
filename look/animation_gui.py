"""Native original-GIF TV; QMovie decodes on demand without caching every frame."""
import random
import time
from PySide6.QtCore import Qt,QTimer
from PySide6.QtGui import QMovie
from PySide6.QtWidgets import QApplication,QWidget,QVBoxLayout,QHBoxLayout,QLabel,QPushButton
import animation_tv

class TV(QWidget):
    def __init__(self):
        super().__init__();self.setWindowTitle('Gypsy Astronaut · LOOK');self.resize(1000,760)
        self.seed=random.SystemRandom().randrange(2**63);self.offset=0;self.held=False;self.key=None;self.movie=None;self.started=time.monotonic()
        self.stop=animation_tv.start();layout=QVBoxLayout(self);self.art=QLabel('Preparing saved animations…');self.art.setAlignment(Qt.AlignmentFlag.AlignCenter);self.art.setMinimumSize(1,1);layout.addWidget(self.art,1);self.caption=QLabel();self.caption.setWordWrap(True);layout.addWidget(self.caption)
        bar=QHBoxLayout();layout.addLayout(bar)
        for text,callback in [('← Previous',lambda:self.step(-1)),('Hold / Resume',self.hold),('Next →',lambda:self.step(1)),('Fullscreen · f',self.fullscreen)]:
            button=QPushButton(text);button.clicked.connect(callback);bar.addWidget(button)
        self.setStyleSheet('QWidget {background:#0b1118;color:#eee9df} QPushButton {padding:12px;background:#243548;border:1px solid #b49b65;border-radius:5px}')
        self.timer=QTimer(self);self.timer.timeout.connect(self.tick);self.timer.start(100);self.show()
    def step(self,n):self.offset+=n;self.tick()
    def hold(self):
        self.held=not self.held
        if self.held:self.frozen=time.monotonic()-self.started
        else:self.started=time.monotonic()-self.frozen
    def fullscreen(self):self.showNormal() if self.isFullScreen() else self.showFullScreen()
    def tick(self):
        elapsed=self.frozen if self.held else time.monotonic()-self.started
        row,path=animation_tv.choose(elapsed,seed=self.seed,step_offset=self.offset)
        if path and str(path)!=self.key:
            if self.movie:self.movie.stop();self.movie.deleteLater()
            self.key=str(path);self.movie=QMovie(str(path));self.movie.frameChanged.connect(self.draw);self.movie.start();self.caption.setText(row['title'])
    def draw(self):
        if self.movie:self.art.setPixmap(self.movie.currentPixmap().scaled(self.art.size(),Qt.AspectRatioMode.KeepAspectRatio,Qt.TransformationMode.SmoothTransformation))
    def keyPressEvent(self,event):
        if event.key()==Qt.Key.Key_Right:self.step(1)
        elif event.key()==Qt.Key.Key_Left:self.step(-1)
        elif event.key()==Qt.Key.Key_Space:self.hold()
        elif event.key()==Qt.Key.Key_F:self.fullscreen()
        elif event.key()==Qt.Key.Key_Escape:self.showNormal() if self.isFullScreen() else self.close()
    def closeEvent(self,event):self.stop.set();event.accept()

if __name__=='__main__':
    app=QApplication([]);window=TV();app.exec()
