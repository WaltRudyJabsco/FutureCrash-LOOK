from core.ui_model import actions, build_ui_model


def sample():
    return {
        "nodes": {
            "self": {
                "name": "m3",
                "capabilities": {"filesystem": True, "signal": False, "ollama": True},
                "inference": {"models": [{"name": "gemma", "declared": ["vision", "tools"]}]},
            },
            "peers": [
                {"name": "3090", "node": {
                    "name": "3090",
                    "capabilities": {"filesystem": True, "comfyui": True},
                    "inference": {"models": []},
                }}
            ],
        },
        "health": {"ok": True},
        "jobs": {"jobs": [{"id": "done", "status": "done"}, {"id": "live", "status": "working"}]},
        "services": {"services": {"ollama": {"state": "active"}}},
        "events": {"events": [{"seq": 1, "type": "progress"}]},
    }


def test_ui_model_aggregates_nodes_capabilities_and_active_jobs():
    ui = build_ui_model(sample())
    assert ui["schema"] == "fabric-ui-v1"
    assert ui["summary"]["node_count"] == 2
    assert ui["summary"]["active_jobs"] == 1
    caps = {row["id"]: row for row in ui["capabilities"]}
    assert caps["filesystem"]["count"] == 2
    assert caps["comfyui"]["providers"] == ["3090"]
    assert caps["model.vision"]["providers"] == ["m3:gemma"]
    assert ui["jobs"][0]["id"] == "live"


def test_actions_are_shared_and_mini_only_changes_presentation():
    full = {a["id"]: a for a in actions()}
    mini = {a["id"]: a for a in actions(mini=True)}
    assert full["mini"]["label"] == "mini"
    assert mini["mini"]["label"] == "full"
    assert not full["watch"].get("hidden", False)
    assert mini["watch"]["hidden"] is True
    assert full["restart"]["dangerous"] is True
