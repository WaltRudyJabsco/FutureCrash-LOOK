import sys
from pathlib import Path
from unittest.mock import Mock
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'look'))
import task_state,printing
from core import cognition


def test_session_survives_new_instance_and_isolates_users(tmp_path,monkeypatch):
    monkeypatch.setattr(task_state,'root',lambda:tmp_path)
    with task_state.session('signal:a') as (state,save):
        printing.PrintConversation(state,save).begin('print a packing list')
    with task_state.session('signal:b') as (state,save):
        assert printing.PrintConversation(state,save).begin('yes')=='yes'
    with task_state.session('signal:a') as (state,save):
        task=printing.PrintConversation(state,save)
        assert task.begin('send it')=='print a packing list'
        task.finish()
    with task_state.session('signal:a') as (state,save):
        assert printing.PrintConversation(state,save).begin('yes')=='yes'


def test_expired_task_never_restores_authority(tmp_path,monkeypatch):
    monkeypatch.setattr(task_state,'root',lambda:tmp_path)
    with task_state.session('albert:a') as (state,save):state['request']='print secrets'
    monkeypatch.setattr(task_state.time,'time',lambda:10**12)
    with task_state.session('albert:a') as (state,save):assert not state.get('request')


def test_claim_saved_before_uncertain_send(tmp_path,monkeypatch):
    monkeypatch.setattr(task_state,'root',lambda:tmp_path)
    monkeypatch.setattr(printing,'quick_text',Mock(side_effect=RuntimeError('connection lost')))
    with task_state.session('signal:a') as (state,save):
        task=printing.PrintConversation(state,save);task.begin('print hello on Desk')
        with pytest.raises(RuntimeError):
            printing.run_tool('print_text',{'queue':'Desk','text':'hello'},tmp_path,task.request,{'on_print_attempt':task.finish})
        assert not state['request']
    with task_state.session('signal:a') as (state,save):assert not state['request']


@pytest.mark.parametrize('prompt,read,write',[
 ('print the forecast','printers_list','print_text'),
 ('add this to my Home note','notebook_read','notebook_update'),
 ('play music','media_search','media_play'),
 ('copy this file','read_file','copy_path'),
])
def test_read_receipt_does_not_complete_requested_effect(prompt,read,write):
    goal=cognition.new_goal(prompt,cognition.analyze(prompt,use_openjev=False))
    assert not cognition.assess(goal,successful_tools=[read],final_text='Done')['satisfied']
    assert cognition.assess(goal,successful_tools=[write],final_text='Done')['satisfied']


def test_print_outcomes_are_not_transport_success():
    for state in ('prepared','uncertain','failed','cancelled'):
        assert not cognition.action_result_completed('print_design',{'state':state})
    assert cognition.action_result_completed('print_text',{'state':'queued'})


def test_weather_print_keeps_action_tools(monkeypatch):
    import lo_engine
    monkeypatch.setattr(lo_engine,"_CORE",None)
    monkeypatch.setattr(lo_engine,"_lk_path",lambda:Path(__file__).resolve().parents[1]/"look/lk")
    core=lo_engine._load_core()
    assert not core._lo_weather_only_query('Print a three-day forecast')
    assert core._lo_weather_only_query('What is the weather today?')


def test_browser_engine_restores_host_state_without_chat_history(tmp_path,monkeypatch):
    import lo_engine
    monkeypatch.setattr(task_state,'root',lambda:tmp_path)
    seen=[]
    def fake(prompt,task_context=None,**kwargs):
        state,save=task_context
        task=printing.PrintConversation(state,save)
        seen.append(task.begin(prompt))
        return {'text':'pending'}
    monkeypatch.setattr(lo_engine,'_chat_once',fake)
    lo_engine.chat_once('print a recipe',session_id='signal:test')
    lo_engine.chat_once('Little Printer',session_id='signal:test')
    lo_engine.chat_once('send it',session_id='signal:test')
    lo_engine.chat_once('send it',session_id='albert:other')
    assert seen==['print a recipe','print a recipe on Little Printer','print a recipe on Little Printer','send it']
