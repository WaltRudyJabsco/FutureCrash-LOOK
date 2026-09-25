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
        self.assertIn('media_intent=None if force_search else _lo_media_intent_profile(prompt,profile)', self.source)
        self.assertIn('def _lo_media_decision_intent(prompt,profile="workspace"):', self.source)
        self.assertIn('/v1/decisions/shadow', self.source)
        self.assertIn('cannot turn "play Talking Heads" into an internet search', self.source)

    def test_media_ordinals_and_single_worker_reuse_are_present(self):
        self.assertIn('"play first track":"first"', self.source)
        self.assertIn('"play first song on album":"first_album"', self.source)
        self.assertIn('def _media_jump_ordinal(action):', self.source)
        self.assertIn('["loadlist",str(MEDIA_QUEUE_FILE),"replace"]', self.source)

    def test_selector_queue_is_canonical_only(self):
        start=self.source.index('def _media_queue_append(rows):')
        end=self.source.index('def _media_selector(', start)
        body=self.source[start:end]
        self.assertNotIn('_media_entry_source(row)', body)
        self.assertNotIn('["loadfile"', body)

    def test_media_selector_uses_look_multiselect_semantics(self):
        self.assertIn('if key=="\\t" and visible:', self.source)
        self.assertIn('Tab select · Enter/P play · Q queue · A queue matches', self.source)
        self.assertIn('if key=="C":', self.source)
        self.assertIn('if key=="S" and chosen:', self.source)
        self.assertNotIn('Space queue · A play matches', self.source)


if __name__ == "__main__":
    unittest.main()
