import unittest
from unittest.mock import patch
from core import node


class ControlPlaneTests(unittest.TestCase):
    def test_http_server_has_defensive_backlog(self):
        self.assertGreaterEqual(node.FabricHTTPServer.request_queue_size, 64)
        self.assertTrue(node.FabricHTTPServer.daemon_threads)


    def test_local_and_tailscale_ingress_use_distinct_backends(self):
        self.assertEqual(node.DEFAULT_PORT, 7332)
        self.assertEqual(node.DEFAULT_INGRESS_PORT, 7333)
        self.assertNotEqual(node.DEFAULT_PORT, node.DEFAULT_INGRESS_PORT)

    def test_http_pressure_meter_tracks_and_releases_requests(self):
        meter = node.HTTPMetrics("test")
        meter.accepted_connection()
        rid = meter.start("GET", "/v1/nodes", "127.0.0.1")
        live = meter.public()
        self.assertEqual(live["accepted"], 1)
        self.assertEqual(live["active"], 1)
        self.assertEqual(live["by_endpoint"]["GET /v1/nodes"], 1)
        meter.finish(rid)
        done = meter.public()
        self.assertEqual(done["active"], 0)
        self.assertEqual(done["completed"], 1)

    def test_advertisement_reads_cache_without_rebuilding(self):
        cached = {
            "protocol": 1,
            "version": node.VERSION,
            "identity": {"name": "cached", "hostname": "cached"},
            "platform": {"system": "test", "architecture": "test"},
            "capabilities": {},
            "inference": {"available": False, "models": [], "resident": [], "preferred_model": None},
            "supervisor": {"active": None},
            "runtime": {"ok": True},
            "pulse": {"epoch": "unix-1s-v1", "number": 0, "period_ms": 1000},
        }
        with node.ADVERTISEMENT_LOCK:
            old = dict(node.ADVERTISEMENT_CACHE)
            node.ADVERTISEMENT_CACHE.clear()
            node.ADVERTISEMENT_CACHE.update(cached)
        try:
            with patch.object(node, "_build_advertisement", side_effect=AssertionError("hot path rebuilt advertisement")):
                out = node.advertisement()
            self.assertEqual(out["identity"]["name"], "cached")
        finally:
            with node.ADVERTISEMENT_LOCK:
                node.ADVERTISEMENT_CACHE.clear()
                node.ADVERTISEMENT_CACHE.update(old)

    def test_failed_unknown_peer_is_backed_off(self):
        registry = node.PeerRegistry()
        rows = [{"name": "phone", "dns": "phone.example.ts.net", "ips": ["100.1.2.3"], "online": True}]
        clock = [1000.0]
        calls = []
        def fail(url, data=None, timeout=2.0):
            calls.append(url)
            raise TimeoutError("not a node")
        with patch.object(node, "peer_rows", return_value=rows), \
             patch.object(node, "now", side_effect=lambda: clock[0]), \
             patch.object(node, "http_json", side_effect=fail), \
             patch.object(node.random, "uniform", return_value=0.0):
            registry.refresh()
            self.assertEqual(len(calls), 1)
            clock[0] += 5.0
            registry.refresh()
            self.assertEqual(len(calls), 1, "unknown peer was re-probed before backoff expired")


if __name__ == "__main__":
    unittest.main()
