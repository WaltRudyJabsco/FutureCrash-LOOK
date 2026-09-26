import importlib.util
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("media_core", ROOT / "look" / "media_core.py")
media_core = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(media_core)


class MediaCoreTests(unittest.TestCase):
    def test_fast_scan_builds_artist_album_track_index_without_hashing(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / "music"
            album = root / "Talking Heads" / "Remain in Light"
            album.mkdir(parents=True)
            (album / "01 Born Under Punches.flac").write_bytes(b"not-real-audio")
            (album / "02 Crosseyed and Painless.mp3").write_bytes(b"not-real-audio")
            (album / "cover.jpg").write_bytes(b"image")

            library = media_core.scan_root(root)
            self.assertEqual(library["schema"], "look-media-library-v1")
            self.assertEqual(len(library["entries"]), 2)
            first = library["entries"][0]
            self.assertEqual(first["artist"], "Talking Heads")
            self.assertEqual(first["album"], "Remain in Light")
            self.assertEqual(first["track"], 1)
            self.assertEqual(first["title"], "Born Under Punches")
            self.assertNotIn("digest", first)

    def test_query_prefers_whole_album_and_session_owns_queue(self):
        library = {
            "roots": ["/music"],
            "entries": [
                {"path": "/music/Talking Heads/Remain in Light/01.flac", "artist": "Talking Heads", "album": "Remain in Light", "title": "Born Under Punches", "track": 1},
                {"path": "/music/Talking Heads/Remain in Light/02.flac", "artist": "Talking Heads", "album": "Remain in Light", "title": "Crosseyed and Painless", "track": 2},
                {"path": "/music/Miles/Kind of Blue/01.flac", "artist": "Miles Davis", "album": "Kind of Blue", "title": "So What", "track": 1},
            ],
        }
        rows = media_core.resolve_query(library, "Remain in Light")
        self.assertEqual([r["track"] for r in rows], [1, 2])
        session = media_core.new_session(rows)
        self.assertEqual(session["schema"], "look-media-session-v1")
        self.assertEqual(len(session["queue"]), 2)
        self.assertEqual(session["current_index"], 0)
        self.assertEqual(session["state"], "stopped")

    def test_saved_playlist_contains_queue_not_player_runtime(self):
        session = media_core.new_session([
            {"path": "/music/a.flac", "artist": "A", "title": "One"},
            {"path": "/music/b.flac", "artist": "A", "title": "Two"},
        ])
        session["pid"] = 1234
        session["position"] = 42.0
        saved = media_core.playlist_payload("Driving", session)
        self.assertEqual(saved["schema"], "look-media-playlist-v1")
        self.assertEqual(len(saved["queue"]), 2)
        self.assertNotIn("pid", saved)
        self.assertNotIn("position", saved)


if __name__ == "__main__":
    unittest.main()
