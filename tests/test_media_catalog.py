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


def test_overlapping_roots_are_one_physical_file_and_forget_preserves_specific_scan(tmp_path):
    root=tmp_path/'music';album=root/'Artist'/'Album';album.mkdir(parents=True)
    track=album/'01 Song.mp3';track.write_bytes(b'audio')
    broad=media_core.scan_root(root)
    merged=media_core.scan_root(album,broad)
    assert len(merged['entries'])==1
    assert merged['entries'][0]['root']==str(album)
    forgotten=media_core.forget_root(merged,root)
    assert len(forgotten['entries'])==1 and forgotten['roots']==[str(album)]
    assert track.read_bytes()==b'audio'


def test_ts_source_is_not_media_but_transport_packets_are(tmp_path):
    root=tmp_path/'music';root.mkdir()
    (root/'component.ts').write_text('export const Song = "not a movie";')
    packets=b''.join(b'G'+bytes(187) for _ in range(4))
    (root/'concert.ts').write_bytes(packets)
    scanned=media_core.scan_root(root)
    assert [Path(row['path']).name for row in scanned['entries']]==['concert.ts']


def test_broad_rescan_updates_changed_file_without_reassigning_specific_root(tmp_path):
    root=tmp_path/'music';album=root/'Artist'/'Album';album.mkdir(parents=True)
    track=album/'01 Song.mp3';track.write_bytes(b'first')
    library=media_core.scan_root(album)
    library['entries'][0]['digest']='sha256:old'
    track.write_bytes(b'changed content')
    rescanned=media_core.scan_root(root,library)
    assert len(rescanned['entries'])==1
    row=rescanned['entries'][0]
    assert row['root']==str(album) and row['bytes']==len(b'changed content')
    assert 'digest' not in row
