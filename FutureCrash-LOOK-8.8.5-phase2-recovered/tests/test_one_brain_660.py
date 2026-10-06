from pathlib import Path
import importlib.util
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'core'))
sys.path.insert(0,str(ROOT/'look'))
import cognition
import lo_engine


def test_fuzzy_router_handles_typos_without_exposing_every_tool():
    route=cognition.analyze('headlienes',use_openjev=False)
    assert route.primary=='web'
    assert route.confidence >= .72
    assert 'web_search' in route.allowed_tools
    assert 'search_files' not in route.allowed_tools
    assert 'run_command' not in route.allowed_tools


def test_compound_request_unions_capability_neighborhoods():
    route=cognition.analyze('give me the headlines and read the top one aloud',use_openjev=False)
    assert route.primary=='web'
    assert 'speech' in route.families
    assert 'web_search' in route.allowed_tools
    assert 'audio_speak' in route.allowed_tools
    assert 'search_files' not in route.allowed_tools


def test_media_and_system_language_are_narrowed_before_inference():
    media=cognition.analyze('play something by Talking Heads',use_openjev=False)
    assert media.primary=='media'
    assert {'media_play','media_search'} <= set(media.allowed_tools)
    assert 'web_search' not in media.allowed_tools
    system=cognition.analyze('what is running on port 7330',use_openjev=False)
    assert system.primary=='system'
    assert 'listening_ports' in system.allowed_tools
    assert 'media_play' not in system.allowed_tools


def test_fuzzy_name_resolver_returns_evidence_not_execution():
    result=cognition.resolve_name('little ipad',[
        {'id':'ep-a','name':'iPad Mini','aliases':['little ipad']},
        {'id':'ep-b','name':'Office M4'},
    ])
    assert result['status']=='resolved'
    assert result['item']['id']=='ep-a'
    assert result['confidence'] >= .78


def test_goal_and_satisfaction_are_explicit_machine_state():
    route=cognition.analyze('speak this aloud',use_openjev=False)
    goal=cognition.new_goal('speak this aloud',route)
    no_receipt=cognition.assess(goal,successful_tools=[],final_text='Sure.')
    assert no_receipt['satisfied'] is False
    receipt=cognition.assess(goal,successful_tools=['audio_speak'],final_text='Spoken.')
    assert receipt['satisfied'] is True


def test_lo_engine_exposes_shared_route_and_registry():
    assert lo_engine.route_intent('headlienes')=='web_current'
    route=lo_engine.analyze_request('play something by Talking Heads')
    assert route['primary']=='media'
    ids={row['id'] for row in lo_engine.action_registry()}
    assert {'web.search','files.search','media.play','audio.speak'} <= ids


def test_node_advertises_cognition_and_action_registry():
    node=(ROOT/'core'/'node.py').read_text()
    assert '"cognition.route": True' in node
    assert '"action.registry": True' in node
    assert 'if path == "/v1/actions"' in node
    assert 'if path == "/v1/cognition/route"' in node


def test_lo_scopes_tools_from_shared_route_and_emits_goal_receipts():
    core=(ROOT/'look'/'lk').read_text()
    assert 'tools = _lo_tools_for_route(profile,turn_route)' in core
    assert 'events.emit("tools_scoped"' in core
    assert 'events.emit("goal_started"' in core
    assert 'events.emit("goal_verified"' in core


def test_compound_plan_is_explicit_dependency_data():
    route=cognition.analyze('give me the headlines and read the top one aloud',use_openjev=False)
    plan=cognition.build_plan('give me the headlines and read the top one aloud',route)
    assert plan['schema']=='fabric-plan-v1'
    assert [step['family'] for step in plan['steps']][:2]==['web','speech']
    assert plan['steps'][1]['depends_on']==['step_1']
    assert 'audio.speak' in plan['steps'][1]['actions']


def test_decision_plane_facade_keeps_route_plan_verify_together():
    plane=cognition.DecisionPlane(use_openjev=False)
    route=plane.route('headlienes')
    assert route.primary=='web'
    goal=plane.goal('speak this aloud')
    assert plane.verify(goal,successful_tools=['audio_speak'],final_text='Spoken.')['satisfied'] is True

def test_installer_installs_and_verifies_cognition_core():
    install=(ROOT/'install.sh').read_text()
    assert 'core/cognition.py' in install
    assert 'installed Fabric cognition core differs from release' in install
    assert 'import conductor, fabric_client, memory_store, decision, cognition' in install
