import json
import tempfile
import threading
import unittest
import urllib.request
import urllib.error
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "core"))
import node
from fabric_packet import ArtifactStore


class ArtifactStreamingTests(unittest.TestCase):
    def test_file_backed_artifact_does_not_copy_media_bytes(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            source = root / "track.flac"
            source.write_bytes(b"0123456789" * 1024)
            store = ArtifactStore(root / "artifacts")
            meta = store.register_file(source)
            digest_hex = meta["digest"].split(":", 1)[1]
            self.assertEqual(meta["storage"], "external")
            self.assertEqual(meta["bytes"], source.stat().st_size)
            self.assertFalse((root / "artifacts" / digest_hex).exists())
            resolved_meta, resolved = store.path_for(meta["digest"])
            self.assertEqual(resolved, source.resolve())
            self.assertEqual(resolved_meta["media_type"], "audio/flac")

    def test_register_file_does_not_weaken_existing_managed_copy(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            store = ArtifactStore(root / "artifacts")
            managed = store.put(b"same", media_type="application/octet-stream")
            source = root / "copy.bin"
            source.write_bytes(b"same")
            registered = store.register_file(source)
            self.assertEqual(registered["digest"], managed["digest"])
            self.assertEqual(registered["storage"], "managed")

    def test_registered_file_change_invalidates_artifact(self):
        with tempfile.TemporaryDirectory() as td:
            source = Path(td) / "movie.mp4"
            source.write_bytes(b"abcdef")
            store = ArtifactStore(Path(td) / "artifacts")
            meta = store.register_file(source)
            source.write_bytes(b"changed-size")
            with self.assertRaises(OSError):
                store.path_for(meta["digest"])


    def test_artifact_catalog_lists_metadata_without_payload_reads(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            source = root / "song.flac"
            source.write_bytes(b"catalog me")
            store = ArtifactStore(root / "artifacts")
            meta = store.register_file(source)
            rows = store.list_metadata()
            self.assertEqual([row["digest"] for row in rows], [meta["digest"]])
            self.assertEqual(rows[0]["storage"], "external")

    def test_byte_range_parser(self):
        self.assertEqual(node._parse_byte_range(None, 100), (0, 99, False))
        self.assertEqual(node._parse_byte_range("bytes=10-19", 100), (10, 19, True))
        self.assertEqual(node._parse_byte_range("bytes=90-", 100), (90, 99, True))
        self.assertEqual(node._parse_byte_range("bytes=-8", 100), (92, 99, True))
        with self.assertRaises(ValueError):
            node._parse_byte_range("bytes=100-120", 100)
        with self.assertRaises(ValueError):
            node._parse_byte_range("bytes=0-1,4-5", 100)

    def test_http_range_stream_and_public_metadata(self):
        old_store = node.ARTIFACTS
        server = None
        thread = None
        try:
            with tempfile.TemporaryDirectory() as td:
                source = Path(td) / "sample.mp4"
                source.write_bytes(bytes(range(256)) * 8)
                node.ARTIFACTS = ArtifactStore(Path(td) / "artifacts")
                meta = node.ARTIFACTS.register_file(source)
                server = node.FabricHTTPServer(("127.0.0.1", 0), node.API, plane="local")
                thread = threading.Thread(target=server.serve_forever, daemon=True)
                thread.start()
                base = f"http://127.0.0.1:{server.server_address[1]}/v1/artifacts/{meta['digest']}"

                req = urllib.request.Request(base, headers={"Range": "bytes=100-149"})
                with urllib.request.urlopen(req, timeout=2) as response:
                    data = response.read()
                    self.assertEqual(response.status, 206)
                    self.assertEqual(response.headers.get("Accept-Ranges"), "bytes")
                    self.assertEqual(response.headers.get("Content-Range"), f"bytes 100-149/{source.stat().st_size}")
                    self.assertEqual(data, source.read_bytes()[100:150])

                with urllib.request.urlopen(base + "?meta=1", timeout=2) as response:
                    public = json.load(response)["artifact"]
                self.assertNotIn("path", public)
                self.assertNotIn("mtime_ns", public)
                self.assertTrue(public["range"])
                self.assertTrue(public["stream"])

                head = urllib.request.Request(base, method="HEAD")
                with urllib.request.urlopen(head, timeout=2) as response:
                    self.assertEqual(response.status, 200)
                    self.assertEqual(response.headers.get("Accept-Ranges"), "bytes")
                    self.assertEqual(int(response.headers.get("Content-Length")), source.stat().st_size)
                    self.assertEqual(response.read(), b"")
        finally:
            if server is not None:
                server.shutdown()
                server.server_close()
            if thread is not None:
                thread.join(timeout=2)
            node.ARTIFACTS = old_store


if __name__ == "__main__":
    unittest.main()
