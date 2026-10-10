from unittest.mock import Mock
import pytest
from core import notifications as alerts


def test_settings_are_durable_and_voice_is_opt_in(tmp_path,monkeypatch):
    monkeypatch.setattr(alerts,'settings_path',lambda:tmp_path/'notifications.json')
    assert alerts.settings()=={'desktop':True,'sound':True,'voice':False}
    alerts.settings({'voice':True,'sound':False});assert alerts.settings()['voice'] is True
    with pytest.raises(ValueError):alerts.settings({'voice':'yes'})


def test_macos_notification_text_is_an_argument_not_code(monkeypatch):
    monkeypatch.setattr(alerts.sys,'platform','darwin');monkeypatch.setattr(alerts.shutil,'which',lambda name:name)
    run=Mock(return_value=Mock(returncode=0,stderr=''));monkeypatch.setattr(alerts.subprocess,'run',run)
    text='" & do shell script "bad"'
    result=alerts.deliver('Reminder',text,{'desktop':True,'sound':True})
    assert result['ok']
    command=run.call_args.args[0]
    assert command[-2]==text and text not in command[2]
    assert 'shell' not in run.call_args.kwargs


def test_linux_notification_and_missing_backend_receipts(monkeypatch):
    monkeypatch.setattr(alerts.sys,'platform','linux');monkeypatch.setattr(alerts.shutil,'which',lambda name:name if name=='notify-send' else None)
    run=Mock(return_value=Mock(returncode=0,stderr=''));monkeypatch.setattr(alerts.subprocess,'run',run)
    assert alerts.deliver('Reminder','Text',{'desktop':True,'sound':False})['ok']
    assert run.call_args.args[0]==['notify-send','--app-name=Fabric','--','Reminder','Text']
    monkeypatch.setattr(alerts.shutil,'which',lambda name:None)
    assert not alerts.deliver('Reminder','Text',{'desktop':True,'sound':True})['ok']
