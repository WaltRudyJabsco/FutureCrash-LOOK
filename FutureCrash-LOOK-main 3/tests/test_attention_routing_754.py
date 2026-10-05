from core.attention import normalize_event, plan_voice_targets


def _inventory():
    nodes=[
        {"name":"3090","capabilities":{"audio.speak":True}},
        {"name":"mac-air","capabilities":{"audio.speak":True}},
        {"name":"silent-node","capabilities":{"audio.speak":False}},
    ]
    endpoints=[
        {"endpoint_id":"ep-ipad","label":"This iPad","surface":"albert","capabilities":["audio.speak"],"metadata":{"device":"iPad"}},
        {"endpoint_id":"ep-display","label":"Display only","surface":"browser","capabilities":["display.output"],"metadata":{}},
    ]
    return nodes,endpoints


def test_attention_event_is_typed_and_defaults_to_voice_origin():
    event=normalize_event({"message":"  Image   generation is ready. "})
    assert event["schema"]=="fabric-attention-v1"
    assert event["message"]=="Image generation is ready."
    assert event["channels"]==["voice"]
    assert event["target"]=="origin"


def test_all_means_all_current_speech_capable_nodes_and_browser_endpoints():
    nodes,endpoints=_inventory()
    event=normalize_event({"message":"Ready","target":"all"})
    plan=plan_voice_targets(event,local_node="3090",nodes=nodes,endpoints=endpoints)
    assert plan["status"]=="ready"
    assert [(r["kind"],r["target"]) for r in plan["targets"]]==[
        ("node","3090"),("node","mac-air"),("endpoint","ep-ipad")
    ]


def test_named_browser_endpoint_can_be_targeted_without_guessing():
    nodes,endpoints=_inventory()
    event=normalize_event({"message":"Ready","target":"ipad"})
    plan=plan_voice_targets(event,local_node="3090",nodes=nodes,endpoints=endpoints)
    assert plan["status"]=="ready"
    assert plan["targets"][0]["target"]=="ep-ipad"


def test_active_and_follow_me_are_reserved_but_never_guessed():
    nodes,endpoints=_inventory()
    for target in ("active","follow-me"):
        plan=plan_voice_targets(normalize_event({"message":"Need you","target":target}),local_node="3090",nodes=nodes,endpoints=endpoints)
        assert plan["status"]=="presence-unresolved"
        assert plan["targets"]==[]
