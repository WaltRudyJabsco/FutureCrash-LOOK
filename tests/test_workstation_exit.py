import importlib.util
from pathlib import Path
import queue
import os
import termios
import time
import sys
import threading
from types import SimpleNamespace
from unittest.mock import Mock

ROOT=Path(__file__).resolve().parents[1]
SPEC=importlib.util.spec_from_file_location('workstation_exit_test',ROOT/'future-crash/future_crash.py')
FC=importlib.util.module_from_spec(SPEC); sys.modules[SPEC.name]=FC; SPEC.loader.exec_module(FC)


def app():
    instance=FC.FutureCrash.__new__(FC.FutureCrash)
    instance.mode='work'; instance.input='draft'; instance.cursor=5
    instance.work_detached=False; instance.deferred_submit=('work','queued')
    instance.ask_detached=False
    instance.work_log=[]; instance.work_history=[]; instance.work_pending_user='request'
    instance.pending_tool={'name':'weather'}; instance.pending_tool_origin='work'
    instance.pending_tool_visible_text=''; instance.pending_tool_history=[]
    instance.host_results=queue.Queue(); instance.busy=False
    instance.tool_return_mode='work'; instance.audio=SimpleNamespace(cue=Mock())
    instance.host=SimpleNamespace(capability=Mock(return_value='WEATHER'))
    instance.set_mode=lambda mode:setattr(instance,'mode',mode)
    instance._ask_oracle=Mock()
    return instance


def test_escape_responds_while_host_is_blocked_and_late_result_stays_closed():
    instance=app(); started=threading.Event(); release=threading.Event()
    def execute(request):
        started.set(); release.wait(2); return True,'Sunny'
    instance.host.execute=execute
    instance._execute_pending_tool()
    assert started.wait(1)
    assert instance.mode=='work'
    instance.handle_key('ESC')
    assert instance.mode=='ambient'
    assert instance.deferred_submit is None
    release.set()
    instance._finish_host_tool(*instance.host_results.get(timeout=2))
    assert instance.mode=='ambient'
    assert not instance.busy
    assert any('Sunny' in text for role,text in instance.work_log)
    instance._ask_oracle.assert_not_called()


def test_escape_denies_pending_tool_and_returns_to_ambient():
    instance=app(); instance.mode='tool_approval'
    instance.handle_key('ESC')
    assert instance.mode=='ambient'
    assert instance.pending_tool is None
    assert instance.work_detached


def test_late_model_tool_proposal_does_not_reopen_workstation():
    instance=app(); instance.handle_key('ESC')
    instance._queue_tool_request({'name':'weather'},'work','Late proposal')
    assert instance.mode=='ambient'
    assert instance.work_pending_user is None
    assert not instance.busy


def test_answer_enter_then_escape_stays_closed_after_late_reply():
    instance=app(); instance.mode='answer'; instance.input=''; instance.cursor=0
    instance.handle_key('\r'); instance.handle_key('ESC')
    instance.term=SimpleNamespace(key=lambda:None)
    instance.inference=SimpleNamespace(end=Mock())
    instance.oracle=SimpleNamespace(responses=queue.Queue())
    instance.oracle.responses.put(('ask','Late answer',None,{}))
    instance.poll()
    assert instance.mode=='ambient'
    assert instance.answer=='Late answer'
    assert instance.deferred_submit is None


def test_terminal_recovers_canonical_echo_and_reads_escape_without_return():
    master,slave=os.openpty()
    try:
        terminal=FC.Terminal.__new__(FC.Terminal); terminal.fd=slave
        settings=termios.tcgetattr(slave)
        settings[3]|=termios.ICANON|termios.ECHO
        termios.tcsetattr(slave,termios.TCSANOW,settings)
        os.write(master,b'\x1b')
        assert terminal.key()=='ESC'
        assert not termios.tcgetattr(slave)[3] & (termios.ICANON|termios.ECHO)
    finally:
        os.close(master); os.close(slave)


def test_shared_lo_output_capture_is_isolated_from_parent_tui(tmp_path,monkeypatch):
    future=tmp_path/'future-crash'; future.mkdir()
    look=tmp_path/'look'; look.mkdir()
    (future/'lo_worker.py').write_text((ROOT/'future-crash/lo_worker.py').read_text())
    marker=tmp_path/'active'
    (look/'lo_engine.py').write_text('''import contextlib,io,time,sys
from pathlib import Path
def chat_once(**payload):
    assert not sys.stdin.isatty()
    with contextlib.redirect_stdout(io.StringIO()):
        Path('''+repr(str(marker))+''').write_text('active')
        time.sleep(.15)
        print('Captured worker diagnostics')
    return {'text':payload['prompt']}
''')
    monkeypatch.setattr(FC,'__file__',str(future/'future_crash.py'))
    result=[]; failures=[]; before=sys.stdout
    def run():
        try: result.append(FC._shared_lo_chat('Hello'))
        except Exception as exc: failures.append(exc)
    worker=threading.Thread(target=run); worker.start()
    deadline=time.monotonic()+2
    while not marker.exists() and time.monotonic()<deadline: time.sleep(.01)
    assert marker.exists()
    assert sys.stdout is before
    worker.join(2)
    assert not failures
    assert result==[{'text':'Hello'}]
