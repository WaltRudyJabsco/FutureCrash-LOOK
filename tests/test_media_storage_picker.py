import importlib.machinery
import importlib.util
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock
import sys
import pytest

ROOT=Path(__file__).resolve().parents[1]

@pytest.fixture
def lk(monkeypatch,tmp_path):
    monkeypatch.setenv('HOME',str(tmp_path))
    loader=importlib.machinery.SourceFileLoader('lk_storage_picker',str(ROOT/'look/lk'))
    spec=importlib.util.spec_from_loader(loader.name,loader)
    module=importlib.util.module_from_spec(spec);loader.exec_module(module)
    monkeypatch.setattr(module,'sys',SimpleNamespace(path=sys.path,stdin=SimpleNamespace(isatty=lambda:True),stdout=SimpleNamespace(isatty=lambda:True),stderr=sys.stderr))
    monkeypatch.setitem(sys.modules,'recovery_setup',SimpleNamespace(mounted_drives=lambda **kw:[]))
    monkeypatch.setattr(module.shutil,'which',lambda name:None)
    return module


def test_picker_decline_never_creates_folders_or_changes_preference(lk,monkeypatch,tmp_path):
    answers=iter(['c',str(tmp_path/'Library'),'n'])
    monkeypatch.setattr('builtins.input',lambda prompt:next(answers))
    assert lk._media_storage_pick()==0
    assert not (tmp_path/'Library').exists()
    assert not (tmp_path/'.config/look/media_storage.json').exists()


def test_picker_confirm_uses_existing_storage_command(lk,monkeypatch,tmp_path):
    answers=iter(['c',str(tmp_path/'Library'),'y'])
    monkeypatch.setattr('builtins.input',lambda prompt:next(answers))
    save=Mock(return_value=0);monkeypatch.setattr(lk,'_media_storage_command',save)
    assert lk._media_storage_pick()==0
    save.assert_called_once_with(['--node','local','--root',str(tmp_path/'Library')])


def test_picker_invalid_home_root_never_saves(lk,monkeypatch,tmp_path):
    answers=iter(['c',str(tmp_path)])
    monkeypatch.setattr('builtins.input',lambda prompt:next(answers))
    save=Mock();monkeypatch.setattr(lk,'_media_storage_command',save)
    assert lk._media_storage_pick()==1
    save.assert_not_called()


def test_settings_opens_library_picker(lk,monkeypatch):
    save=Mock(return_value=0);monkeypatch.setattr(lk,'_media_storage_command',save)
    assert lk._settings_action('medialibrary')==0
    save.assert_called_once_with(['--pick'])


def test_search_picker_escape_does_not_save(lk,monkeypatch):
    monkeypatch.setattr(lk.shutil,'which',lambda name:'/usr/bin/fzf')
    pick=Mock(return_value=SimpleNamespace(returncode=130,stdout=''))
    monkeypatch.setattr(lk.subprocess,'run',pick)
    save=Mock();monkeypatch.setattr(lk,'_media_storage_command',save)
    assert lk._media_storage_pick()==0
    save.assert_not_called()
    assert pick.call_args.args[0][0]=='fzf'
