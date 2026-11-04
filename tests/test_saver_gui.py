"""Real Qt rendering with offscreen windows, plus display lifecycle simulation."""
import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
import sys
from pathlib import Path
from unittest.mock import Mock
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'look'))
pytest.importorskip('PySide6')
from PySide6.QtCore import QEvent, Qt
from PySide6.QtGui import QKeyEvent
from PySide6.QtWidgets import QApplication
import saver
import saver_gui

@pytest.fixture(scope='module')
def app():return QApplication.instance() or QApplication(['saver-test'])


def test_real_window_paints_and_escape_quits_all(app,tmp_path,monkeypatch):
    control=saver_gui.SaverController(app,{**saver.defaults(),'scene':'Dune Sea','palette':'mercury'},preview=True,seed=42)
    try:
        app.processEvents()
        window=next(iter(control.windows.values()))
        pixmap=window.grab()
        assert not pixmap.isNull()
        assert pixmap.save(str(tmp_path/'preview.png'))
        quit=Mock();monkeypatch.setattr(app,'quit',quit)
        window.keyPressEvent(QKeyEvent(QEvent.Type.KeyPress,Qt.Key.Key_Escape,Qt.KeyboardModifier.NoModifier))
        quit.assert_called_once()
    finally:
        control.timer.stop()
        for window in control.windows.values():window.removing=True;window.close()


class Screen:
    def __init__(self,name):self.label=name
    def name(self):return self.label
    def serialNumber(self):return self.label


def test_all_displays_matching_and_hotplug(monkeypatch):
    one,two=Screen('one'),Screen('two')
    control=object.__new__(saver_gui.SaverController)
    control.app=Mock();control.app.screens.return_value=[one,two]
    control.settings={**saver.defaults(),'independent':False};control.preview=False
    control.current=one;control.windows={};control.seed=12;control.presentation=None;control.stopping=False
    factory=Mock(side_effect=lambda *_:Mock())
    monkeypatch.setattr(saver_gui,'SaverWindow',factory)
    control.reconcile()
    assert len(control.windows)==2
    assert [call.args[-1] for call in factory.call_args_list]==[12,12]
    removed=control.windows[two]
    control.reconcile(exclude=two)
    assert len(control.windows)==1 and removed.removing
    removed.close.assert_called_once()
    control.app.quit.assert_not_called()
    control.settings['display']='current';control.current=two
    control.reconcile()
    assert list(control.windows)==[two]
    control.app.screens.return_value=[];control.reconcile()
    control.app.quit.assert_called_once()



def test_mac_presentation_restores_original_options_once():
    native=object.__new__(saver_gui.MacPresentation)
    native.application=123;native.original=None
    native.selector=lambda name:name
    native.get_options=Mock(return_value=0)
    native.set_options=Mock()
    native.enter();native.enter()
    native.get_options.assert_called_once()
    assert native.set_options.call_args.args[-1]==native.HIDE_DOCK | native.HIDE_MENU_BAR
    native.restore();native.restore()
    assert native.set_options.call_args_list[-1].args[-1]==0
    assert native.set_options.call_count==3


def test_preview_never_enters_native_presentation(app,monkeypatch):
    factory=Mock();monkeypatch.setattr(saver_gui,'MacPresentation',factory)
    control=saver_gui.SaverController(app,saver.defaults(),preview=True,seed=1)
    try:
        factory.assert_not_called()
        window=next(iter(control.windows.values()))
        assert not window.windowFlags() & Qt.WindowType.FramelessWindowHint
    finally:
        control.timer.stop()
        for window in control.windows.values():window.removing=True;window.close()


def test_dismiss_restores_presentation_before_closing_any_window():
    events=[]
    control=object.__new__(saver_gui.SaverController)
    control.stopping=False;control.timer=Mock()
    control.presentation=Mock();control.presentation.restore.side_effect=lambda:events.append('restore')
    window=Mock();window.close.side_effect=lambda:events.append('close')
    control.windows={'display':window}
    control.app=Mock();control.app.quit.side_effect=lambda:events.append('quit')
    control.dismiss();control.dismiss()
    assert events==['restore','close','quit']
    assert window.removing
    control.settle_presentation()
    control.presentation.enter.assert_not_called()


def test_mac_settling_reapplies_every_full_display_rectangle():
    control=object.__new__(saver_gui.SaverController)
    control.stopping=False;control.presentation=Mock()
    screens=[Mock(),Mock(),Mock()];windows=[Mock(),Mock(),Mock()]
    control.windows=dict(zip(screens,windows))
    control.settle_presentation()
    control.presentation.enter.assert_called_once()
    for screen,window in control.windows.items():window.setGeometry.assert_called_once_with(screen.geometry())


def test_running_keys_reserve_colors_visuals_and_explicit_dismissal(app,monkeypatch):
    control=saver_gui.SaverController(app,saver.defaults(),preview=True,seed=1)
    try:
        window=next(iter(control.windows.values()))
        change=Mock();dismiss=Mock()
        monkeypatch.setattr(control,'change_visual',change);monkeypatch.setattr(control,'dismiss',dismiss)
        for key in (Qt.Key.Key_C,Qt.Key.Key_V,Qt.Key.Key_A,Qt.Key.Key_Q):
            window.keyPressEvent(QKeyEvent(QEvent.Type.KeyPress,key,Qt.KeyboardModifier.NoModifier))
        assert [call.kwargs for call in change.call_args_list]==[{'color':True},{'color':False}]
        dismiss.assert_not_called()
        window.keyPressEvent(QKeyEvent(QEvent.Type.KeyPress,Qt.Key.Key_C,Qt.KeyboardModifier.NoModifier,'c',True))
        assert change.call_count==2
        for key in (Qt.Key.Key_Space,Qt.Key.Key_Escape):
            window.keyPressEvent(QKeyEvent(QEvent.Type.KeyPress,key,Qt.KeyboardModifier.NoModifier))
        assert dismiss.call_count==2
    finally:
        control.timer.stop()
        for window in control.windows.values():window.removing=True;window.close()


def test_live_controls_reach_every_display():
    control=object.__new__(saver_gui.SaverController)
    import time
    control.started=time.monotonic()
    windows=[Mock(),Mock(),Mock()];control.windows=dict(enumerate(windows))
    control.change_visual(color=True);control.change_visual(color=False)
    for window in windows:
        window.run.next_color.assert_called_once()
        window.run.next_scene.assert_called_once()
        assert window.update.call_count==2


def test_museum_draws_cached_artwork_in_existing_saver(app,tmp_path,monkeypatch):
    from PySide6.QtGui import QImage,QColor
    import museum_art
    path=tmp_path/'art.png';art=QImage(100,100,QImage.Format.Format_RGB32);art.fill(QColor('#5588aa'));art.save(str(path))
    monkeypatch.setattr(museum_art,'artwork',lambda phase:({'title':'Fixture artwork','artist':'Artist','museum':'Museum'},path))
    control=saver_gui.SaverController(app,{**saver.defaults(),'scene':'Museum'},preview=True,seed=1)
    try:
        app.processEvents();window=next(iter(control.windows.values()));image=window.grab().toImage()
        assert window.museum_key==str(path)
        assert image.pixelColor(image.width()//2,image.height()//2).name()=='#5588aa'
        cached=window.museum_scaled.cacheKey();window.grab();assert window.museum_scaled.cacheKey()==cached
    finally:
        control.timer.stop()
        for window in control.windows.values():window.removing=True;window.close()


def test_ascii_museum_uses_distinct_display_slots_and_cached_render(app,tmp_path,monkeypatch):
    from PySide6.QtGui import QImage,QColor
    import museum_art,museum_cache
    monkeypatch.setattr(museum_cache,'start',lambda:None)
    path=tmp_path/'art.png';image=QImage(30,30,QImage.Format.Format_RGB32);image.fill(QColor('#8899aa'));image.save(str(path))
    phases=[]
    monkeypatch.setattr(museum_art,'artwork',lambda phase:phases.append(phase) or ({'title':'Art','artist':'Artist'},path))
    monkeypatch.setattr(museum_art,'symbols',lambda *args:[' .:-=+*#%@']*5)
    control=saver_gui.SaverController(app,dict(saver.defaults(),enabled=['ASCII Museum']),preview=True,seed=1)
    try:
        window=next(iter(control.windows.values()));window.museum_slot=0;window.grab()
        first=window.ascii_museum_key;window.museum_slot=1;window.grab()
        assert first[-2:]!=window.ascii_museum_key[-2:]
        assert phases[-1]>=20
        cached=window.ascii_museum.cacheKey();window.grab();assert cached==window.ascii_museum.cacheKey()
    finally:control.dismiss()


def test_museum_arrow_keys_advance_display_sets(app,monkeypatch):
    import museum_cache
    monkeypatch.setattr(museum_cache,'start',lambda:None)
    control=saver_gui.SaverController(app,dict(saver.defaults(),scene='Museum'),preview=True,seed=1)
    try:
        window=next(iter(control.windows.values()))
        window.keyPressEvent(QKeyEvent(QEvent.Type.KeyPress,Qt.Key.Key_Right,Qt.KeyboardModifier.NoModifier))
        assert control.museum_step==len(control.windows)
        window.keyPressEvent(QKeyEvent(QEvent.Type.KeyPress,Qt.Key.Key_Left,Qt.KeyboardModifier.NoModifier))
        assert control.museum_step==0 and not control.stopping
    finally:control.dismiss()
