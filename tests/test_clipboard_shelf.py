import os
import subprocess
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from look import clipboard_shelf as clip, notebook, look_renderer as renderer
from look.notebook_core import Notebook
from look.notebook_markdown import cell_width


@pytest.fixture
def shelf(tmp_path):
    value = clip.Shelf(tmp_path/'clipboard')
    yield value
    value.close()


@pytest.fixture
def terminal(monkeypatch,capsys):
    monkeypatch.setattr(clip.sys, 'stdin', SimpleNamespace(fileno=lambda:0,isatty=lambda:True))
    monkeypatch.setattr(clip.termios, 'tcgetattr', lambda *args:['old'])
    monkeypatch.setattr(clip.termios, 'tcsetattr', Mock())
    monkeypatch.setattr(clip.tty, 'setraw', lambda *args:None)
    monkeypatch.setattr(clip.tty, 'setcbreak', lambda *args:None)
    monkeypatch.setattr(clip, 'ensure_watcher', Mock())
    return SimpleNamespace(getvalue=lambda:capsys.readouterr().out)


def test_bounded_history_unicode_multiline_and_private_storage(shelf):
    assert not shelf.enabled
    for i in range(12):
        shelf.observe(f'{i}: café 日本語 👩‍💻\nsecond line\t')
    rows = shelf.rows()
    assert len(rows) == 10
    assert rows[0][1].startswith('11:') and rows[-1][1].startswith('2:')
    assert rows[0][1].endswith('\nsecond line\t')
    assert shelf.root.stat().st_mode & 0o777 == 0o700
    assert (shelf.root/'history.sqlite3').stat().st_mode & 0o777 == 0o600


def test_deleted_current_clip_does_not_reappear_or_touch_clipboard(shelf, monkeypatch):
    copied = Mock(); monkeypatch.setattr(clip, 'copy_clipboard', copied)
    shelf.observe('current')
    assert not shelf.observe('current')
    shelf.remove(shelf.rows()[0][0])
    assert not shelf.observe('current') and shelf.rows() == []
    shelf.observe('new'); shelf.clear()
    assert not shelf.observe('new') and shelf.rows() == []
    copied.assert_not_called()


def test_unsupported_oversized_and_empty_do_not_consume_slots(shelf):
    for text in [None, '', 'a'*(clip.TEXT_LIMIT+1)]:
        assert not shelf.observe(text)
    assert shelf.rows() == []


def test_disabled_history_does_not_start_or_read_clipboard(tmp_path, monkeypatch):
    monkeypatch.setattr(clip, 'directory', lambda:tmp_path/'clipboard')
    read = Mock(); launch = Mock()
    monkeypatch.setattr(clip, 'read_clipboard', read)
    monkeypatch.setattr(clip.subprocess, 'Popen', launch)
    clip.ensure_watcher()
    assert not (tmp_path/'clipboard').exists()
    shelf = clip.Shelf(); shelf.close()
    clip.ensure_watcher()
    read.assert_not_called(); launch.assert_not_called()


@pytest.mark.parametrize('slot,key', list(enumerate('!@#$%^&*()')))
def test_shift_number_mapping_and_enhanced_keyboard(slot, key):
    assert clip.removal_slot(key) == slot
    assert clip.removal_slot(f'\033[{ord(clip.SLOTS[slot])};2u') == slot
    assert clip.removal_slot('paste:'+key) is None
    assert clip.removal_slot('\033[999999999;2u') is None


def test_recall_tenth_slot_and_copy_failure_keeps_shelf_open(shelf, terminal, monkeypatch):
    for i in range(10): shelf.observe(str(i))
    copy = Mock(side_effect=[False,True]); monkeypatch.setattr(clip,'copy_clipboard',copy)
    keys = iter(['0','1'])
    assert clip.show(shelf=shelf, reader=lambda *args:next(keys)) == '9'
    assert [call.args[0] for call in copy.call_args_list] == ['0','9']
    assert 'Clipboard write failed' in terminal.getvalue()
    assert clip.termios.tcsetattr.call_args.args[-1] == ['old']


def test_remove_reindexes_and_escape_leaves_system_clipboard(shelf, terminal, monkeypatch):
    shelf.observe('old'); shelf.observe('new')
    copy = Mock(); monkeypatch.setattr(clip,'copy_clipboard',copy)
    keys = iter(['!','esc'])
    assert clip.show(shelf=shelf,reader=lambda *args:next(keys)) is None
    assert [row[1] for row in shelf.rows()] == ['old']
    copy.assert_not_called()


def test_preview_back_then_recall_and_terminal_controls_are_inert(shelf, terminal, monkeypatch):
    raw = 'café\n\033]52;c;BAD\a\n\033[31mred'
    shelf.observe(raw)
    copy = Mock(return_value=True); monkeypatch.setattr(clip,'copy_clipboard',copy)
    keys = iter(['enter','down','esc','1'])
    assert clip.show(shelf=shelf,reader=lambda *args:next(keys)) == raw
    output = terminal.getvalue()
    assert '\033]52;c;BAD' not in output
    assert '\\x1b]52;c;BAD\\x07' in output
    copy.assert_called_once_with(raw)


def test_shelf_paste_cannot_recall_delete_or_share(shelf, terminal, monkeypatch):
    shelf.observe('text')
    share = Mock(); copy = Mock()
    monkeypatch.setattr(clip,'share_note',share); monkeypatch.setattr(clip,'copy_clipboard',copy)
    keys = iter(['paste:1!se','esc'])
    clip.show(shelf=shelf,reader=lambda *args:next(keys))
    assert len(shelf.rows()) == 1
    share.assert_not_called(); copy.assert_not_called()


def test_explicit_share_only_selected_clip(shelf, terminal, monkeypatch):
    shelf.observe('first'); shelf.observe('second')
    share = Mock(); monkeypatch.setattr(clip,'share_note',share)
    keys = iter(['down','s','esc'])
    clip.show(shelf=shelf,reader=lambda *args:next(keys))
    share.assert_called_once_with('first')
    assert len(shelf.rows()) == 2


def test_narrow_shelf_rows_fit_terminal_cells(shelf, terminal, monkeypatch):
    shelf.observe('日本語'*80+'\n'+'wide '*40)
    monkeypatch.setattr(clip.shutil,'get_terminal_size',lambda *args:(34,18))
    keys = iter(['enter','esc','esc'])
    clip.show(shelf=shelf,reader=lambda *args:next(keys))
    import re
    plain = re.sub(r'\033\[[0-9;?]*[A-Za-z]', '', terminal.getvalue().replace('\033[2J','\n'))
    assert all(sum(cell_width(char) for char in line)<=33 for line in plain.splitlines())


def test_note_editor_inserts_at_caret_and_uppercase_z_stays_text(shelf, terminal, monkeypatch):
    shelf.observe('日本語\nnext')
    show = Mock(return_value='日本語\nnext'); monkeypatch.setattr(clip,'show',show)
    keys = iter(['left','\x19','Z','\x13'])
    assert notebook.capture_note(0,lambda *args:next(keys),initial_text='ab') == 'a日本語\nnextZb'
    assert show.call_args.kwargs['insert'] is True


def test_notes_list_and_preview_open_shelf_without_changing_query(terminal, tmp_path, monkeypatch):
    store = Notebook(tmp_path/'notes'); store.create('Title\nbody')
    show = Mock(); monkeypatch.setattr(clip,'show',show)
    keys = iter(['Z','esc','esc'])
    notebook.workspace(store,None,lambda *args:next(keys),lambda text,width:text,initial_query='Title')
    keys = iter(['Z','esc'])
    notebook.note_view(store,store.list()[0],lambda *args:next(keys))
    assert show.call_count == 2
    assert 'FILTER Title' in terminal.getvalue()


def test_look_shelf_preserves_filter_query(terminal, tmp_path, monkeypatch):
    monkeypatch.setattr(renderer.sys.stdout,'isatty',lambda:True)
    monkeypatch.setattr(renderer,'NativePreviewController',Mock)
    show = Mock(); monkeypatch.setattr(clip,'show',show)
    path = tmp_path/'notes'; path.mkdir()
    keys = iter(['Z','Q']); monkeypatch.setattr(renderer,'read_key',lambda **kwargs:next(keys))
    queries = []
    def candidates(query):
        queries.append(query); return [path]
    renderer.pager(['row'],24,80,rebuild=lambda *args:['row'],candidates=candidates,
                   force_interactive=True,initial_query='notes')
    show.assert_called_once()
    assert queries and set(queries) == {'notes'}


def test_backend_failures_are_reported_without_losing_text(monkeypatch):
    monkeypatch.setattr(clip,'backend',lambda:(['fake-read'],['fake-copy']))
    monkeypatch.setattr(clip.subprocess,'run',Mock(side_effect=subprocess.TimeoutExpired('fake',1)))
    assert clip.read_clipboard() is None
    assert clip.copy_clipboard('retained') is False


def test_pasted_digits_are_one_inert_ui_event():
    import pty
    master,slave = pty.openpty()
    previous = clip.termios.tcgetattr(slave)
    try:
        clip.tty.setraw(slave)
        os.write(master,b'\033[200~1!se\n\033[201~')
        assert clip.read_key(slave,.2) == 'paste:'
        assert clip.read_key(slave,.01) == ''
    finally:
        clip.termios.tcsetattr(slave,clip.termios.TCSADRAIN,previous)
        os.close(master); os.close(slave)


@pytest.mark.parametrize('sequence,expected',[(b'\033[49;2u','\033[49;2u'),
    (b'\033[27u','esc'),(b'\033[13u','\r'),(b'\033[99;5u','\x03'),(b'\033[49u','1')])
def test_enhanced_shelf_keys(sequence,expected):
    import pty
    master,slave = pty.openpty()
    try:
        clip.tty.setraw(slave); os.write(master,sequence)
        assert clip.read_key(slave,.2) == expected
    finally:
        os.close(master); os.close(slave)


def test_watcher_samples_only_enabled_and_exits_on_disable(shelf,monkeypatch):
    monkeypatch.setattr(clip,'directory',lambda:shelf.root)
    read = Mock(return_value='background text'); monkeypatch.setattr(clip,'read_clipboard',read)
    sleep = Mock(side_effect=lambda seconds:shelf.set('enabled','0'))
    monkeypatch.setattr(clip.time,'sleep',sleep)
    clip.watch()
    read.assert_not_called()
    shelf.set('enabled','1'); clip.watch()
    read.assert_called_once(); sleep.assert_called_once_with(clip.POLL_SECONDS)
    assert shelf.rows()[0][1] == 'background text'


def test_locked_watcher_does_not_spawn_or_capture_a_second_time(shelf,monkeypatch):
    monkeypatch.setattr(clip,'directory',lambda:shelf.root)
    shelf.set('enabled','1')
    monkeypatch.setattr(clip,'backend',lambda:(['reader'],['writer']))
    read = Mock(); launch = Mock()
    monkeypatch.setattr(clip,'read_clipboard',read)
    monkeypatch.setattr(clip.subprocess,'Popen',launch)
    with (shelf.root/'watch.lock').open('a') as lock:
        clip.fcntl.flock(lock,clip.fcntl.LOCK_EX|clip.fcntl.LOCK_NB)
        clip.ensure_watcher(); clip.watch()
    launch.assert_not_called(); read.assert_not_called()


def test_disabled_during_read_does_not_capture_one_more_item(shelf,monkeypatch):
    monkeypatch.setattr(clip,'directory',lambda:shelf.root)
    shelf.set('enabled','1')
    def read():
        shelf.set('enabled','0'); return 'must not capture'
    monkeypatch.setattr(clip,'read_clipboard',read)
    monkeypatch.setattr(clip.time,'sleep',lambda *args:None)
    clip.watch()
    assert shelf.rows() == []


def test_ui_numbers_do_not_move_when_another_app_copies(shelf,terminal,monkeypatch):
    shelf.observe('original')
    copy = Mock(return_value=True); monkeypatch.setattr(clip,'copy_clipboard',copy)
    def read(*args):
        shelf.observe('arrived after frame'); return '1'
    assert clip.show(shelf=shelf,reader=read) == 'original'
    copy.assert_called_once_with('original')


def test_ui_cancel_and_exception_restore_terminal(shelf,terminal):
    def failed(*args): raise OSError('terminal disconnected')
    with pytest.raises(OSError,match='disconnected'):
        clip.show(shelf=shelf,reader=failed)
    assert clip.termios.tcsetattr.call_args.args[-1] == ['old']


def test_share_is_a_normal_note_and_unicode_controls_are_safe(tmp_path,monkeypatch):
    from look import notebook_core
    store = Notebook(tmp_path/'notes')
    monkeypatch.setattr(notebook_core,'Notebook',lambda:store)
    nudge = Mock(); monkeypatch.setattr(notebook,'nudge_sync',nudge)
    clip.share_note('Title 日本語\n\033]52;c;BAD\a')
    row = store.list()[0]
    assert row['project'] == 'Clipboard'
    assert '\033' not in row['body'] and '\\x1b' in row['body']
    assert len(store.list()) == 1
    nudge.assert_called_once()


def wayland(monkeypatch):
    monkeypatch.setattr(clip.sys,'platform','linux')
    monkeypatch.setenv('WAYLAND_DISPLAY','wayland-test')
    monkeypatch.setenv('XDG_SESSION_TYPE','wayland')
    monkeypatch.setattr(clip.shutil,'which',lambda name:'/tools/'+name)


def test_wayland_watch_is_event_driven_and_never_polls(shelf,monkeypatch):
    import io
    wayland(monkeypatch);monkeypatch.setattr(clip,'directory',lambda:shelf.root);shelf.set('enabled','1')
    read=Mock(side_effect=AssertionError('Wayland must not poll'));monkeypatch.setattr(clip,'read_clipboard',read)
    process=Mock(pid=123456);process.poll.side_effect=[None,1]
    launch=Mock(return_value=process);monkeypatch.setattr(clip.subprocess,'Popen',launch)
    def event(_):
        monkeypatch.setattr(clip.sys,'stdin',io.StringIO('Café 日本語\nSecond line'))
        monkeypatch.setenv('CLIPBOARD_STATE','data');clip.capture_stdin();shelf.set('enabled','0')
    monkeypatch.setattr(clip.time,'sleep',event)
    clip.watch()
    args=launch.call_args.args[0]
    assert '--watch' in args and args[-1]=='--capture-stdin'
    assert launch.call_args.kwargs['stdin']==clip.subprocess.DEVNULL
    assert launch.call_args.kwargs['start_new_session']
    assert shelf.rows()[0][1]=='Café 日本語\nSecond line'
    read.assert_not_called()


def test_unsupported_wayland_watch_does_not_retry_or_fall_back(shelf,monkeypatch):
    wayland(monkeypatch);monkeypatch.setattr(clip,'directory',lambda:shelf.root);shelf.set('enabled','1')
    process=Mock();process.poll.return_value=1
    launch=Mock(return_value=process);monkeypatch.setattr(clip.subprocess,'Popen',launch)
    read=Mock(side_effect=AssertionError('No polling fallback'));monkeypatch.setattr(clip,'read_clipboard',read)
    clip.watch();clip.ensure_watcher();clip.watch();clip.sample_automatic(shelf)
    assert launch.call_count==1 and 'unavailable' in clip.capture_description(shelf)
    assert shelf.enabled and shelf.rows()==[]
    read.assert_not_called()


@pytest.mark.parametrize('state',['sensitive','nil','clear','future-unknown'])
def test_wayland_callback_ignores_non_data_states(shelf,monkeypatch,state):
    import io
    monkeypatch.setattr(clip,'directory',lambda:shelf.root);shelf.set('enabled','1')
    monkeypatch.setenv('CLIPBOARD_STATE',state);monkeypatch.setattr(clip.sys,'stdin',io.StringIO('not stored'))
    clip.capture_stdin();assert shelf.rows()==[]


def test_wayland_enable_and_popup_do_not_read_clipboard(shelf,terminal,monkeypatch):
    wayland(monkeypatch);monkeypatch.setattr(clip,'directory',lambda:shelf.root)
    read=Mock(side_effect=AssertionError('No unsolicited Wayland read'));monkeypatch.setattr(clip,'read_clipboard',read)
    assert clip.main(['on'])==0
    clip.show(fd=0,reader=lambda *a:'esc',shelf=shelf)
    read.assert_not_called()


def test_explicit_add_works_with_capture_off(shelf,monkeypatch):
    wayland(monkeypatch);monkeypatch.setattr(clip,'directory',lambda:shelf.root)
    monkeypatch.setattr(clip,'read_clipboard',lambda:'Explicit clip')
    assert clip.main(['add'])==0
    assert not shelf.enabled and shelf.rows()[0][1]=='Explicit clip'


def test_wayland_failed_spawn_is_not_retried(shelf, monkeypatch):
    wayland(monkeypatch)
    monkeypatch.setattr(clip, 'directory', lambda: shelf.root)
    shelf.set('enabled', '1')
    launch = Mock(side_effect=OSError('helper removed'))
    monkeypatch.setattr(clip.subprocess, 'Popen', launch)
    clip.watch()
    clip.ensure_watcher()
    launch.assert_called_once()
    assert 'unavailable' in clip.capture_description(shelf)


def test_wayland_opt_out_stops_owned_event_process(shelf, monkeypatch):
    wayland(monkeypatch)
    monkeypatch.setattr(clip, 'directory', lambda: shelf.root)
    shelf.set('enabled', '1')
    process = Mock(pid=123456)
    process.poll.return_value = None
    monkeypatch.setattr(clip.subprocess, 'Popen', Mock(return_value=process))
    monkeypatch.setattr(clip.time, 'sleep', lambda _: shelf.set('enabled', '0'))
    terminate = Mock()
    monkeypatch.setattr(clip.os, 'killpg', terminate)
    clip.watch()
    terminate.assert_called_once_with(process.pid, clip.signal.SIGTERM)
    process.wait.assert_called_once_with(timeout=2)
    assert not shelf.enabled


def test_wayland_without_display_does_not_poll_xwayland(shelf, monkeypatch):
    wayland(monkeypatch)
    monkeypatch.delenv('WAYLAND_DISPLAY')
    shelf.set('enabled', '1')
    read = Mock(side_effect=AssertionError('No XWayland fallback'))
    monkeypatch.setattr(clip, 'read_clipboard', read)
    clip.sample_automatic(shelf)
    read.assert_not_called()
