"""Render a real artwork in the existing saver, offscreen and without user-display changes."""
import os,json,sys
from pathlib import Path
os.environ['QT_QPA_PLATFORM']='offscreen'
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'look'))
from PySide6.QtWidgets import QApplication
import museum_art,saver,saver_gui
fixture=ROOT/'artifacts/museum-live';row=json.loads((fixture/'catalog.json').read_text())['items'][0]
path=fixture/'collection/images'/(row['id']+'.jpg');museum_art.artwork=lambda phase:(row,path)
app=QApplication(['museum-preview']);control=saver_gui.SaverController(app,{**saver.defaults(),'scene':'Museum'},preview=True,seed=1)
app.processEvents();window=next(iter(control.windows.values()));image=window.grab();out=ROOT/'artifacts/museum-browser/saver.png';out.parent.mkdir(parents=True,exist_ok=True);assert image.save(str(out))
control.timer.stop()
for window in control.windows.values():window.removing=True;window.close()
print('Real-art Museum saver rendered with existing Qt display controller')
