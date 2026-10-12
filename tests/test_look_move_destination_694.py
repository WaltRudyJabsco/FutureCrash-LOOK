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


def test_prompt_path_completion_picker_clear_and_unicode(tmp_path,monkeypatch,capsys):
    import io,re
    from look import look_renderer as renderer
    class Input:
        def fileno(self):return 0
    monkeypatch.setattr(renderer.sys,'stdin',Input())
    monkeypatch.setattr(renderer.termios,'tcgetattr',lambda fd:[])
    monkeypatch.setattr(renderer.termios,'tcsetattr',lambda *args:None)
    monkeypatch.setattr(renderer.tty,'setcbreak',lambda fd:None)
    monkeypatch.setattr(renderer.shutil,'get_terminal_size',lambda *args:__import__('os').terminal_size((40,20)))
    folder=tmp_path/'Média With Spaces';folder.mkdir()
    raw=bytearray(b'\x15'+str(tmp_path/'Méd').encode()+b'\t\r')
    monkeypatch.setattr(renderer.os,'read',lambda fd,n:bytes([raw.pop(0)]))
    value,cancel=renderer.prompt_line('Destination › ',initial='/long/default',picker_root=tmp_path)
    assert value==str(folder)+'/' and not cancel
    raw[:]=b'\x1b[C\r'
    monkeypatch.setattr(renderer.select,'select',lambda *args:([0],[],[]) if raw else ([],[],[]))
    picks=[]
    monkeypatch.setattr(renderer,'_destination_picker',lambda path:picks.append(path) or folder)
    value,cancel=renderer.prompt_line('Destination › ',initial=str(tmp_path),picker_root=tmp_path)
    assert picks==[tmp_path] and value==str(folder)+'/' and not cancel
    output=re.sub(r'\x1b\[[0-9;]*[A-Za-z]','',capsys.readouterr().out)
    assert all(len(segment)<=39 for segment in output.split('\r') if '\n' not in segment)
