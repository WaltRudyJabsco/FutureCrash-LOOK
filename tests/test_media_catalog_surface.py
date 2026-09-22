import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class MediaCatalogSurfaceTests(unittest.TestCase):
    def test_node_exposes_local_and_fabric_catalogs(self):
        source = (ROOT / "core" / "node.py").read_text(encoding="utf-8")
        self.assertIn('path == "/v1/media/catalog"', source)
        self.assertIn('path == "/v1/media/fabric"', source)
        self.assertIn('path == "/v1/artifacts/fabric"', source)
        self.assertIn('path == "/v1/media/identify"', source)

    def test_look_find_uses_selector_not_exact_name_roundtrip(self):
        source = (ROOT / "look" / "lk").read_text(encoding="utf-8")
        self.assertIn('def _media_selector(', source)
        self.assertIn('Enter/P play', source)
        self.assertIn('Tab select', source)
        self.assertIn('def _media_complete_command(', source)
        self.assertIn('def _media_fabric_command(', source)


if __name__ == "__main__":
    unittest.main()
