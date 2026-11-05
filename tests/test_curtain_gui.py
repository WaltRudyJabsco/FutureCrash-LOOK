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

def test_desktop_submits_on_fourth_digit(app,monkeypatch):
    monkeypatch.setattr(saver_gui,'SaverWindow',curtain_gui.CurtainWindow)
    monkeypatch.setattr(curtain_client,'request',lambda *a,**k:{'locked':True})
    control=curtain_gui.CurtainController(app);submitted=[]
    monkeypatch.setattr(control,'unlock',lambda pin:submitted.append(pin))
    try:
        control.prompt();dialog=control.dialog
        dialog.setTextValue('123');assert not submitted
        dialog.setTextValue('1234');assert submitted==['1234']
    finally:control.dismiss()


def test_they_live_shortcut_and_slow_words(monkeypatch):
    calls=[]
    monkeypatch.setattr(curtain_client,'request',lambda action,**fields:calls.append((action,fields)) or {'ok':True,'locked':True})
    assert curtain_client.main([],'lktl')==0
    assert calls==[('lock',{'variant':'they-live'})]
    assert curtain_gui.they_live_word(100,100)==curtain_gui.they_live_word(111.9,100)
    assert curtain_gui.they_live_word(112,100)!=curtain_gui.they_live_word(100,100)


def test_they_live_paints_white_and_prompts_for_pin(app,monkeypatch):
    monkeypatch.setattr(saver_gui,'SaverWindow',curtain_gui.CurtainWindow)
    monkeypatch.setattr(curtain_client,'request',lambda *a,**k:{'locked':True,'variant':'they-live','revision':int(curtain_gui.time.time()*1e9)})
    control=curtain_gui.CurtainController(app)
    try:
        control.pending.result(timeout=2);control.poll()
        window=next(iter(control.windows.values()));app.processEvents()
        image=window.grab().toImage()
        assert image.pixelColor(0,0).name()=='#ffffff'
        assert control.variant=='they-live'
        window.keyPressEvent(QKeyEvent(QEvent.Type.KeyPress,Qt.Key.Key_C,Qt.KeyboardModifier.NoModifier))
        assert control.dialog is not None and not control.stopping
    finally:control.dismiss()


def test_phrase_slots_are_distinct_and_seeded():
    for step in range(24):
        words=[curtain_gui.they_live_word(step*12,0,slot,123) for slot in range(8)]
        assert len(set(words))==8
        assert words!=[curtain_gui.they_live_word(step*12,0,slot,456) for slot in range(8)]
    assert len({curtain_gui.they_live_word(step*12,0,0,123) for step in range(8)})==8


def test_successful_unlock_collapses_before_dismiss(app,monkeypatch):
    monkeypatch.setattr(saver_gui,'SaverWindow',curtain_gui.CurtainWindow)
    monkeypatch.setattr(curtain_client,'request',lambda *a,**k:{'locked':True,'variant':'they-live'})
    control=curtain_gui.CurtainController(app)
    try:
        control.pending.result(timeout=2);control.poll()
        control.finish_unlock()
        assert control.shutdown_started is not None and not control.stopping
        window=next(iter(control.windows.values()))
        control.shutdown_started=curtain_gui.time.monotonic()-.4
        image=window.grab().toImage()
        assert image.pixelColor(0,0).name()=='#000000'
        assert curtain_gui.crt_shape(0)==(1,1)
        assert curtain_gui.crt_shape(1)==(0,.004)
    finally:control.dismiss()
