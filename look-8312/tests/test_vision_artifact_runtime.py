import base64 as stdlib_base64

from core import node


def test_node_vision_artifact_hydration_has_base64_runtime():
    raw = b"vision-artifact-bytes"
    assert node.base64.b64encode(raw) == stdlib_base64.b64encode(raw)
