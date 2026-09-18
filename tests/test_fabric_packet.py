import tempfile
import unittest
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "core"))
from fabric_packet import ArtifactStore, FabricStore, normalize_packet, packet_digest


class FabricPacketTests(unittest.TestCase):
    def packet(self):
        return normalize_packet({
            "kind": "task",
            "work": {"operation": "fabric.echo", "input": {"hello": "world"}},
            "execution": {"priority": "interactive"},
            "authority": {"principal": "user", "grants": ["observe"]},
        }, origin="test-node")

    def test_digest_is_stable(self):
        p = self.packet()
        self.assertEqual(packet_digest(p), packet_digest(dict(p)))

    def test_idempotency_returns_original_job(self):
        with tempfile.TemporaryDirectory() as td:
            store = FabricStore(Path(td) / "fabric.sqlite3")
            p = self.packet()
            first, created = store.submit(p, node="test-node")
            second, created_again = store.submit(p, node="test-node")
            self.assertTrue(created)
            self.assertFalse(created_again)
            self.assertEqual(first["id"], second["id"])

    def test_artifacts_are_content_addressed(self):
        with tempfile.TemporaryDirectory() as td:
            store = ArtifactStore(Path(td))
            a = store.put(b"same bytes", media_type="text/plain")
            b = store.put(b"same bytes", media_type="text/plain")
            self.assertEqual(a["digest"], b["digest"])
            meta, data = store.get(a["digest"])
            self.assertEqual(data, b"same bytes")
            self.assertEqual(meta["media_type"], "text/plain")


if __name__ == "__main__":
    unittest.main()
