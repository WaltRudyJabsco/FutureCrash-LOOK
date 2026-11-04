import pytest
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt,QEvent
from PySide6.QtGui import QKeyEvent
import curtain_gui,curtain_client,saver_gui

@pytest.fixture
def app():return QApplication.instance() or QApplication([])

def test_escape_prompts_instead_of_dismiss_and_pin_is_masked(app,monkeypatch):
    monkeypatch.setattr(saver_gui,'SaverWindow',curtain_gui.CurtainWindow)
    monkeypatch.setattr(curtain_client,'request',lambda *a,**k:{'locked':True})
    control=curtain_gui.CurtainController(app)
    try:
        window=next(iter(control.windows.values()))
        window.keyPressEvent(QKeyEvent(QEvent.Type.KeyPress,Qt.Key.Key_Escape,Qt.KeyboardModifier.NoModifier))
        assert control.dialog is not None and not control.stopping
        assert control.dialog.textEchoMode()==curtain_gui.QLineEdit.EchoMode.Password
        window.close();assert not control.stopping
    finally:control.dismiss()

def test_remote_unlock_dismisses(app,monkeypatch):
    monkeypatch.setattr(saver_gui,'SaverWindow',curtain_gui.CurtainWindow)
    monkeypatch.setattr(curtain_client,'request',lambda *a,**k:{'locked':False})
    control=curtain_gui.CurtainController(app)
    control.pending.result(timeout=2);control.poll()
    assert control.stopping

def test_cli_shortcut_and_private_pin(monkeypatch):
    calls=[]
    monkeypatch.setattr(curtain_client,'request',lambda action='status',**fields:calls.append((action,fields)) or {'ok':True,'locked':action=='lock'})
    monkeypatch.setattr(curtain_client.getpass,'getpass',lambda _: '1234')
    monkeypatch.setattr(curtain_client,'picker',lambda:42)
    assert curtain_client.main([],'lock')==42
    assert curtain_client.main([],'lk')==0
    assert calls[-1]==('lock',{})
    assert curtain_client.main([],'unlock')==0
    assert calls[-1]==('unlock',{'pin':'1234'})
