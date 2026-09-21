from pathlib import Path

LK = (Path(__file__).resolve().parents[1] / "look" / "lk").read_text()


def test_visual_followups_include_describe_and_identify():
    assert '"describe", "description", "identify", "what is this", "what\'s this"' in LK


def test_direct_vision_contract_present():
    assert "DIRECT VISION INPUT:" in LK
    assert "filename/resource metadata is not a substitute" in LK


def test_preview_tools_are_suppressed_for_normal_attached_image_turns():
    assert '"preview_path","open_path","reveal_path"' in LK
    assert "if not explicit_host_preview" in LK
