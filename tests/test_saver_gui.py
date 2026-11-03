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
