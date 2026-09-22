import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class MediaFabricSourceTests(unittest.TestCase):
    def test_media_cli_preserves_transport_control_and_adds_fabric_streaming(self):
        source = (ROOT / "look" / "lk").read_text(encoding="utf-8")
        block = source[source.index("def _media_fcl_node("):source.index("# --- Starter control surfaces")]
        self.assertIn('if raw in {"stream","open"} or (raw=="play" and len(args)>1):', block)
        self.assertIn('aliases={"play":"toggle"', block)
        self.assertIn('artifact-add', block)
        self.assertIn('--input-ipc-server=', block)
        self.assertIn('play @NODE', block)

    def test_node_advertises_generic_artifact_transport_not_media_server(self):
        source = (ROOT / "core" / "node.py").read_text(encoding="utf-8")
        self.assertIn('"artifact.read": True', source)
        self.assertIn('"artifact.range": True', source)
        self.assertIn('"artifact.stream": True', source)
        self.assertNotIn('"media.server": True', source)


if __name__ == "__main__":
    unittest.main()
