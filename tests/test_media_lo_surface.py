import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class MediaLOSurfaceTests(unittest.TestCase):
    def setUp(self):
        self.source = (ROOT / "look" / "lk").read_text(encoding="utf-8")

    def test_lo_has_first_class_media_tools(self):
        for name in ("media_search", "media_play", "media_queue", "media_control"):
            self.assertIn(f'"name":"{name}"', self.source)
        self.assertIn('For music or media, use media_search/media_play/media_queue/media_control', self.source)

    def test_narrow_media_commands_preflight_before_inference(self):
        self.assertIn('def _lo_media_intent(prompt):', self.source)
        self.assertIn('media_intent=None if force_search else _lo_media_intent(prompt)', self.source)
        self.assertIn('cannot turn "play Talking Heads" into an internet search', self.source)

    def test_media_selector_uses_look_multiselect_semantics(self):
        self.assertIn('if key=="\\t" and visible:', self.source)
        self.assertIn('Tab select · Enter/P play · Q queue · A queue matches', self.source)
        self.assertIn('if key=="C":', self.source)
        self.assertIn('if key=="S" and chosen:', self.source)
        self.assertNotIn('Space queue · A play matches', self.source)


if __name__ == "__main__":
    unittest.main()
