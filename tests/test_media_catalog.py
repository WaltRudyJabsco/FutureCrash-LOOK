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


def test_transport_sync_handles_m2ts_offsets_and_rejects_short_or_text_input(tmp_path):
    stream=tmp_path/'video.ts'
    for packet,offset in ((188,187),(192,4)):
        data=bytearray(offset+3*packet)
        for index in range(3):data[offset+index*packet]=0x47
        stream.write_bytes(data)
        assert media_core.is_media_path(stream)
        stream.write_bytes(data[:offset+2*packet])
        assert not media_core.is_media_path(stream)
    stream.write_text('export const G = "G G G";\n'*50)
    assert not media_core.is_media_path(stream)


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


def test_parent_rescan_removes_deleted_nested_import_but_keeps_other_roots(tmp_path):
    import shutil
    movies=tmp_path/'Movies';old=movies/'Old edition';new=movies/'Widescreen'
    outside=tmp_path/'Offline drive'
    for folder in (old,new,outside):
        folder.mkdir(parents=True);(folder/'movie.mkv').write_bytes(b'movie')
    library=media_core.empty_library()
    for folder in (old,new,outside):library=media_core.scan_root(folder,library)
    shutil.rmtree(old);shutil.rmtree(outside)
    library=media_core.scan_root(movies,library)
    assert {row['path'] for row in library['entries']}=={str(new/'movie.mkv'),str(outside/'movie.mkv')}
    assert next(row for row in library['entries'] if row['path']==str(new/'movie.mkv'))['root']==str(new)


def test_rescan_preserves_unreadable_subtree(monkeypatch,tmp_path):
    root=tmp_path/'Movies';folder=root/'Private';folder.mkdir(parents=True)
    movie=folder/'film.mkv';movie.write_bytes(b'movie')
    library=media_core.scan_root(root)
    def walk(base,onerror):
        onerror(PermissionError(13,'Permission denied',str(folder)))
        yield str(root),[],[]
    monkeypatch.setattr(media_core.os,'walk',walk)
    assert media_core.scan_root(root,library)['entries']==library['entries']
