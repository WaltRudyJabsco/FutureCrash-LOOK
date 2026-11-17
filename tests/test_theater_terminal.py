"""Terminal Theater follows shared owner/ticket/print paths without issuing paper in tests."""
import base64
import json
import os
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock
import pytest
import theater_desk
import theater_terminal as terminal
from core import theater


def test_bare_terminal_entry_opens_desk_but_json_keeps_status(monkeypatch):
    monkeypatch.setattr(theater_desk.sys.stdin,'isatty',lambda:True)
    monkeypatch.setattr(theater_desk.sys.stdout,'isatty',lambda:True)
    run=Mock(return_value=0);desk=Mock(return_value=SimpleNamespace(run=run))
    monkeypatch.setattr(terminal,'Desk',desk)
    ui=object()
    assert theater_desk.main([],ui)==0
    desk.assert_called_once_with(ui,None);run.assert_called_once()
    request=Mock(return_value={'tickets':[]});monkeypatch.setattr(theater_desk,'request',request)
    assert theater_desk.main(['--json'],ui)==0
    request.assert_called_once_with({'action':'status'},'local')


def test_default_host_uses_saved_choice_then_media_owner(tmp_path,monkeypatch):
    monkeypatch.setattr(Path,'home',lambda:tmp_path)
    root=tmp_path/'.config/look';root.mkdir(parents=True)
    (root/'media_storage.json').write_text(json.dumps({'node':'media-owner'}))
    assert terminal.default_host()=='media-owner'
    (root/'theater.json').write_text(json.dumps({'node':'chosen-owner'}))
    assert terminal.default_host()=='chosen-owner'


def test_issue_stores_private_ticket_and_returns_same_invitation(tmp_path,monkeypatch):
    monkeypatch.setattr(Path,'home',lambda:tmp_path)
    desk=terminal.Desk(None,'host');desk.movie={'id':'movie1','title':'Movie'}
    desk.choose=Mock(return_value=24);ticket={'id':'ticket1','code':'CODE','url':'https://host/#CODE','title':'Movie','expires':9999999999}
    desk.call=Mock(return_value=ticket);desk.refresh=Mock();desk.ticket=Mock()
    desk.issue()
    desk.call.assert_called_once_with({'action':'ticket','scope':'movie','hours':24,'media':'movie1'})
    desk.ticket.assert_called_once_with(ticket)
    assert terminal.saved_tickets()['host']['ticket1']==ticket
    assert terminal.ticket_file().stat().st_mode&0o777==0o600
    desk.call.reset_mock();desk.choose.return_value=None;desk.issue();desk.call.assert_not_called()


def test_little_printer_handoff_uses_review_and_same_ticket(tmp_path,monkeypatch):
    import printing
    ticket={'id':'one','code':'ABCDEFGH1234','title':'PCU','expires':9999999999}
    request=Mock(return_value={'png':base64.b64encode(b'\x89PNG\r\n\x1a\nimage').decode()})
    monkeypatch.setattr(terminal,'request',request)
    captures=[]
    def preview(path,ui,**options):
        assert path.is_file();captures.append((path,options));return 0
    monkeypatch.setattr(printing,'selected_file',preview)
    assert terminal.print_ticket(ticket,'host',object(),'Little Printer')==0
    request.assert_called_once_with({'action':'qr','code':'ABCDEFGH1234'},'host')
    path,options=captures[0]
    assert options['queue']=='Little Printer' and options['default_style']=='image'
    assert options['caption'][1]=='ABCDEFGH1234'
    assert not path.exists()


def test_movie_search_filters_before_result_limit(tmp_path,monkeypatch):
    rows=[{'id':str(i),'title':'Song','media_type':'audio/mp3'} for i in range(120)]
    rows.append({'id':'movie','title':'PCU','media_type':'video/mp4'})
    result=theater.admin({'action':'search','kind':'video'},lambda:{'entries':rows},None)
    assert [r['id'] for r in result['items']]==['movie']


def test_real_raw_key_picker_handles_shift_navigation_and_restores_tty(monkeypatch):
    # Test the actual picker using a pseudo-terminal while feeding normalized LK keys.
    import pty
    master,slave=pty.openpty()
    stream=os.fdopen(os.dup(slave),'r')
    monkeypatch.setattr(terminal.sys,'stdin',stream)
    keys=iter(['shiftright','enter'])
    ui=SimpleNamespace(_c=lambda s,c:s,_ansi_clip=lambda s,w:s[:w],_read_tty_key=lambda *a:next(keys))
    before=terminal.termios.tcgetattr(slave)
    try:
        assert terminal.Desk(ui,'host').choose('Movies',[(str(i),i) for i in range(20)])==19
        after=terminal.termios.tcgetattr(slave)
        assert after[0]&terminal.termios.IXON==before[0]&terminal.termios.IXON
        flags=terminal.termios.ECHO|terminal.termios.ICANON|terminal.termios.ISIG
        assert after[3]&flags==before[3]&flags
        ui._read_tty_key=lambda *a:'\x11'
        with pytest.raises(KeyboardInterrupt):terminal.Desk(ui,'host').choose('Quit',[('One',1)])
        after=terminal.termios.tcgetattr(slave)
        assert after[0]&terminal.termios.IXON==before[0]&terminal.termios.IXON
        flags=terminal.termios.ECHO|terminal.termios.ICANON|terminal.termios.ISIG
        assert after[3]&flags==before[3]&flags
    finally:stream.close();os.close(master);os.close(slave)
