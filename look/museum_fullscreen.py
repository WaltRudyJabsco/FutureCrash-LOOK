"""Native fullscreen artwork viewer; slow image and owner requests stay off Qt's loop."""
import json
from pathlib import Path
import subprocess
import sys


def launch(owner,rows,index,playing=False):
    import saver
    runtime=saver.interpreter()
    if runtime is None:raise ValueError('Fullscreen needs the saver graphics runtime: lk saver setup')
    result=subprocess.run([str(runtime),str(Path(__file__))],input=json.dumps(dict(owner=owner,rows=rows,index=index,playing=playing)),text=True)
    if result.returncode:raise ValueError('Fullscreen viewer could not start')


def main(payload):
    from PySide6.QtCore import Qt,QTimer
    from PySide6.QtGui import QPixmap,QCursor
    from PySide6.QtWidgets import QApplication,QWidget,QVBoxLayout,QLabel,QInputDialog
    from museum_desk import Client,Background
    app=QApplication.instance() or QApplication(['LOOK Museum']);client=Client(payload['owner'])
    class Viewer(QWidget):
        def __init__(self):
            super().__init__();self.rows=payload['rows'];self.index=payload['index'];self.playing=payload['playing'];self.image=None;self.future=None;self.kind='';self.ident=''
            self.pool=Background()
            self.setWindowTitle('LOOK Museum');self.setStyleSheet('background:#101719;color:#eeeeea')
            layout=QVBoxLayout(self);self.picture=QLabel();self.picture.setAlignment(Qt.AlignmentFlag.AlignCenter);self.picture.setMinimumSize(1,1);layout.addWidget(self.picture,1)
            self.info=QLabel();self.info.setWordWrap(True);layout.addWidget(self.info)
            self.keys=QLabel('←/→ artwork · Space pause/play · F fullscreen · f favorite · p keep here · m collection · x removal/undo · Esc back');self.keys.setWordWrap(True);self.keys.setStyleSheet('color:#9dbbd7');layout.addWidget(self.keys)
            self.timer=QTimer(self);self.timer.timeout.connect(self.poll);self.timer.start(100)
            self.slides=QTimer(self);self.slides.timeout.connect(self.advance);self.slides.start(10000)
            self.setScreen(app.screenAt(QCursor.pos()) or app.primaryScreen())
            self.showFullScreen();self.load()
        def load(self):
            row=self.rows[self.index];self.ident=row['id'];self.kind='image';self.picture.clear();self.image=None;self.info.setText('Loading '+row['title'])
            self.future=self.pool.submit(client.image,dict(row))
        def label(self):
            row=self.rows[self.index]
            self.info.setText(row['title']+' · '+row.get('artist','')+(' · ★ Favorite' if row.get('favorite') else '')+(' · Removal due '+__import__('time').strftime('%b %d %H:%M',__import__('time').localtime(row['removal_due']))+' · x undo' if row.get('removal_due') else '')+(' · Playing' if self.playing else ' · Paused'))
        def fit(self):
            if self.image:self.picture.setPixmap(self.image.scaled(self.picture.size(),Qt.AspectRatioMode.KeepAspectRatio,Qt.TransformationMode.SmoothTransformation))
        def resizeEvent(self,event):self.fit()
        def advance(self,direction=1):
            if self.future or not self.playing:return
            for step in range(1,len(self.rows)+1):
                index=(self.index+direction*step)%len(self.rows)
                if not self.rows[index].get('removal_due'):
                    self.index=index;self.load();return
            self.playing=False;self.label()
        def poll(self):
            if not self.future or not self.future.done():return
            try:
                result=self.future.result()
                if self.kind=='image':
                    self.image=QPixmap(str(result))
                    if self.image.isNull():raise ValueError('Image could not be decoded')
                    self.fit()
                else:
                    updates={row['id']:row for row in result.get('items',[])}
                    self.rows=[updates.get(row['id'],row) for row in self.rows]
                self.label()
            except Exception as exc:self.info.setText(str(exc))
            self.future=None
        def keyPressEvent(self,event):
            if event.key()==Qt.Key.Key_Escape:self.close();return
            if event.text()=='F':
                self.showNormal() if self.isFullScreen() else self.showFullScreen();return
            if self.future:return
            if event.key() in (Qt.Key.Key_Left,Qt.Key.Key_Right):
                self.index=(self.index+(-1 if event.key()==Qt.Key.Key_Left else 1))%len(self.rows);self.load();self.slides.start(10000);return
            if event.key()==Qt.Key.Key_Space:self.playing=not self.playing;self.label();return
            key=event.text();row=self.rows[self.index]
            if key not in ('f','p','m','x'):return
            self.playing=False;fields={'id':row['id']};action={'f':'favorite','p':'pin','x':'mark-removal'}.get(key)
            if key=='m':
                # Collections come from the already cached owner catalog; no network in this dialog.
                import museum_library
                collections=museum_library.snapshot(client.node).get('collections',{})
                ids=list(collections)
                if not ids:self.info.setText('Create a collection with c in the Museum desk first');return
                labels=[collections[i]['name'] for i in ids]
                choice,ok=QInputDialog.getItem(self,'Collection','Add/remove artwork',labels,0,False)
                if not ok:return
                ident=ids[labels.index(choice)];fields['collection']=ident
                action='collection-remove' if ident in row.get('collections',[]) else 'collection-add'
            self.kind='change';self.future=self.pool.submit(client.change,action,**fields);self.info.setText('Updating artwork…')
        def closeEvent(self,event):
            self.pool.shutdown(wait=False,cancel_futures=True);event.accept()
    viewer=Viewer()
    return app.exec()


if __name__=='__main__':raise SystemExit(main(json.load(sys.stdin)))
