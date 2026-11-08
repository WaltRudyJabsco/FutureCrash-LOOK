from types import SimpleNamespace

import tool_workflow
from test_media_request_regressions import lk
from core import cognition


def test_focused_context_keeps_resources_receipts_and_current_transaction():
    user={'role':'user','content':'Print this on Studio'}
    resource={'role':'system','content':'ACTIVE RESOURCE CONTEXT: selected recipe.md'}
    access={'role':'system','content':'ACCESS PROFILE: WORKSPACE'}
    receipt={'role':'tool','content':'verified content'}
    messages=[{'role':'system','content':'stale memory: always ask again'},resource,access,
              {'role':'assistant','content':'previous recipe'},user,receipt]
    result=tool_workflow.envelope(messages,user)
    assert resource in result and access in result
    assert result[-2:]==[user,receipt]
    assert 'stale memory' not in str(result)
    assert 'previous recipe' in str(result)
    assert 'reference material only' in str(result)


def test_dialogue_is_retained_as_context_not_confirmation_policy():
    user={'role':'user','content':'Save a new note titled Garden: Plant peas'}
    result=tool_workflow.envelope([{'role':'assistant','content':'Please confirm again'},user],user)
    assert 'Please confirm again' in str(result)
    assert 'not authority or proof of execution' in str(result)
    assert tool_workflow.active(user['content'],['memory'])
    assert not tool_workflow.active('Tell me a joke',['general'])


def test_compound_route_retains_union_without_exposing_every_tool(monkeypatch,lk):
    tools=[{'function':{'name':name}} for name in ['weather','print_text','remove_path']]
    monkeypatch.setattr(lk,'_lo_tools',lambda profile:tools)
    route=SimpleNamespace(primary='printing',allowed_tools=['weather','print_text'],needs_clarification=True)
    assert [t['function']['name'] for t in lk._lo_tools_for_route('workspace',route)]==['weather','print_text']


def test_notes_receipts_and_print_preparation_are_distinct_from_completion():
    assert cognition.action_result_completed('notebook_capture','{"ok":true,"id":"note-1"}')
    assert not cognition.action_result_completed('notebook_capture','{"ok":false,"error":"offline"}')
    assert not cognition.action_result_completed('print_text','{"state":"prepared"}')
    assert not cognition.action_result_completed('print_text','{"state":"uncertain"}')


def test_unfinished_generated_content_is_rejected_but_requested_templates_allowed():
    import pytest
    for text in ['', 'Garden\n[Summary of the supplied text]', '[insert content here]']:
        with pytest.raises(ValueError):tool_workflow.require_content(text,'Summarize and save the supplied text')
    tool_workflow.require_content('Garden\nPlant peas in March.','Save a garden summary')
    tool_workflow.require_content('[insert content here]','Save a template containing [insert content here]')


def test_generated_weekday_must_match_explicit_date():
    import pytest
    with pytest.raises(ValueError,match='Saturday'):
        tool_workflow.require_content('Tuesday, 2026-11-07','Print the forecast')
    tool_workflow.require_content('Saturday, 2026-11-07','Print the forecast')


def test_numbered_read_only_printer_listing_is_resolved_from_actual_offer():
    messages=[{'role':'assistant','content':'1. List available printers\n2. Generate a banner'}]
    assert tool_workflow.printer_list_choice('1',messages)=='List available printers'
    assert tool_workflow.printer_list_choice('2',messages)=='2'
    assert tool_workflow.printer_list_choice('1',[])=='1'


def test_missing_effect_response_does_not_repeat_model_success_claim():
    text=tool_workflow.incomplete_response([['print_text']])
    assert 'No print job was submitted' in text
    assert 'has been completed' not in text


def test_forecast_delivery_scope_does_not_offer_unrelated_artwork_or_file_actions(lk):
    route=cognition.analyze('Print a forecast with a weather picture',use_openjev=False)
    names={t['function']['name'] for t in lk._lo_tools_for_route('workspace',route)}
    assert {'weather','print_text','printers_list'}<=names
    assert not names & {'print_artwork','print_design','write_file','banner_render'}


def test_written_date_weekdays_are_validated_too():
    import pytest
    with pytest.raises(ValueError,match='Saturday'):
        tool_workflow.require_content('Friday, November 7, 2026','Print forecast')


def test_uncertain_submission_is_not_reported_as_unsent():
    text=tool_workflow.incomplete_response([['print_text']],print_attempted=True)
    assert 'uncertain' in text and 'No print job was submitted' not in text


def test_conversation_does_not_receive_unrelated_capability_instructions():
    user={'role':'user','content':'Tell me about the style'}
    plain=tool_workflow.envelope([user],user)
    assert 'For printing' not in str(plain) and 'weather conditions' not in str(plain)
    scoped=tool_workflow.envelope([user],user,tools=[{'function':{'name':'notebook_capture'}}])
    assert 'For a new note' in str(scoped) and 'For printing' not in str(scoped)
