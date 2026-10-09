import importlib.util
from pathlib import Path
import queue
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
