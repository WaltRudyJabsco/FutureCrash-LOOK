import importlib.util
import tempfile
import time
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("media_core", ROOT / "look" / "media_core.py")
media_core = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(media_core)


class MediaCatalogTests(unittest.TestCase):
    def test_rescan_preserves_sha_for_unchanged_file(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / "music"
            album = root / "Artist" / "Album"
            album.mkdir(parents=True)
            track = album / "01 Song.flac"
            track.write_bytes(b"abc")
            library = media_core.scan_root(root)
            library["entries"][0]["digest"] = "sha256:" + "a" * 64
            library["entries"][0]["identified_at"] = 123.0

            rescanned = media_core.scan_root(root, library)
            self.assertEqual(rescanned["entries"][0]["digest"], "sha256:" + "a" * 64)
            self.assertEqual(rescanned["entries"][0]["identified_at"], 123.0)

    def test_rescan_drops_sha_when_file_changed(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / "music"
            album = root / "Artist" / "Album"
            album.mkdir(parents=True)
            track = album / "01 Song.flac"
            track.write_bytes(b"abc")
            library = media_core.scan_root(root)
            library["entries"][0]["digest"] = "sha256:" + "a" * 64
            # Force both cheap identity fields to change.
            track.write_bytes(b"different bytes")
            rescanned = media_core.scan_root(root, library)
            self.assertNotIn("digest", rescanned["entries"][0])

    def test_fabric_merge_collapses_sha_copies_and_prefers_local(self):
        digest = "sha256:" + "b" * 64
        rows = [
            {"id": "remote", "node": "3090", "path": "/srv/media/song.flac", "digest": digest,
             "artist": "A", "album": "B", "title": "Song"},
            {"id": "local", "node": "M3", "path": "/Users/me/song.flac", "digest": digest,
             "artist": "A", "album": "B", "title": "Song"},
        ]
        merged = media_core.merge_catalog_entries(rows, local_node="M3")
        self.assertEqual(len(merged), 1)
        self.assertEqual(merged[0]["node"], "M3")
        self.assertEqual(merged[0]["copies"], 2)
        self.assertEqual({x["node"] for x in merged[0]["locations"]}, {"M3", "3090"})

    def test_unidentified_rows_do_not_false_dedupe_across_nodes(self):
        rows = [
            {"id": "same-looking", "node": "3090", "path": "/a/song.mp3", "title": "Song"},
            {"id": "same-looking", "node": "M3", "path": "/b/song.mp3", "title": "Song"},
        ]
        self.assertEqual(len(media_core.merge_catalog_entries(rows, local_node="M3")), 2)

    def test_completion_candidates_prefer_prefix_matches(self):
        rows = [
            {"path": "/x/1", "artist": "Talking Heads", "album": "Remain in Light", "title": "Once in a Lifetime"},
            {"path": "/x/2", "artist": "Talk Talk", "album": "Spirit of Eden", "title": "Desire"},
            {"path": "/x/3", "artist": "Miles Davis", "album": "Kind of Blue", "title": "All Blues"},
        ]
        values = media_core.completion_candidates(rows, "tal")
        self.assertEqual(values[:2], ["Talk Talk", "Talking Heads"])


if __name__ == "__main__":
    unittest.main()
