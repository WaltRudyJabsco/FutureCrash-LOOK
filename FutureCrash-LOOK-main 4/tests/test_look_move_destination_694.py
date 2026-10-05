import os
from pathlib import Path

from look.look_renderer import resolve_action_destination


def test_relative_action_destination_uses_visible_look_directory_not_process_cwd(tmp_path, monkeypatch):
    shell=tmp_path/"shell-home"
    viewed=tmp_path/"work"/"photos"
    shell.mkdir()
    viewed.mkdir(parents=True)
    monkeypatch.chdir(shell)

    resolved=resolve_action_destination("archive", viewed)

    assert resolved == viewed/"archive"
    assert resolved != shell/"archive"


def test_absolute_and_tilde_destinations_keep_their_existing_meaning(tmp_path, monkeypatch):
    viewed=tmp_path/"viewed"
    viewed.mkdir()
    absolute=tmp_path/"elsewhere"/"archive"
    assert resolve_action_destination(str(absolute), viewed) == absolute.resolve()

    home=tmp_path/"home"
    home.mkdir()
    monkeypatch.setenv("HOME", str(home))
    assert resolve_action_destination("~/archive", viewed) == (home/"archive").resolve()
