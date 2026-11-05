"""Render shared cinema visuals without changing user displays."""
import os,sys
from pathlib import Path
os.environ['QT_QPA_PLATFORM']='offscreen'
root=Path(__file__).resolve().parents[1];sys.path.insert(0,str(root/'look'))
from PySide6.QtWidgets import QApplication
import saver,saver_gui,museum_cache
museum_cache.start=lambda:None
app=QApplication(['visual-preview']);out=root/'artifacts/cinema-visuals';out.mkdir(parents=True,exist_ok=True)
for name in ('Number Station','Prism Grid','Parallax Gates','Silk Current'):
    control=saver_gui.SaverController(app,{**saver.defaults(),'scene':name},preview=True,seed=25)
    control.started-=7
    app.processEvents();window=next(iter(control.windows.values()))
    assert window.grab().save(str(out/(name.lower().replace(' ','-')+'.png')))
    control.dismiss()
print('Rendered cinema and gallery motion previews')
