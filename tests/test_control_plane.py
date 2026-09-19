import os
import socket
import tempfile
import threading
import time
import unittest
import urllib.request
from http.server import BaseHTTPRequestHandler
from pathlib import Path
from unittest.mock import patch
from core import node, ingress
from core.fabric_packet import FabricStore


class ControlPlaneTests(unittest.TestCase):
    def test_http_server_has_defensive_backlog(self):
        self.assertGreaterEqual(node.FabricHTTPServer.request_queue_size, 64)
        self.assertTrue(node.FabricHTTPServer.daemon_threads)


    def test_local_node_and_tailscale_ingress_are_distinct_processes(self):
        self.assertEqual(node.DEFAULT_PORT, 7332)
        self.assertEqual(node.DEFAULT_INGRESS_PORT, 0)
        self.assertEqual(ingress.DEFAULT_PORT, 7333)
        self.assertEqual(ingress.DEFAULT_BACKEND_PORT, 7332)
        self.assertLessEqual(ingress.MAX_ACTIVE_REQUESTS, 16)

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


    def test_abrupt_clients_do_not_poison_local_listener(self):
        class TinyHandler(BaseHTTPRequestHandler):
            protocol_version = "HTTP/1.0"
            def log_message(self, *args):
                pass
            def do_GET(self):
                body = b"ok"
                self.send_response(200)
                self.send_header("Content-Length", str(len(body)))
                self.send_header("Connection", "close")
                self.end_headers()
                self.wfile.write(body)

        server = node.FabricHTTPServer(("127.0.0.1", 0), TinyHandler, plane="test-abrupt")
        thread = threading.Thread(target=server.serve_forever, kwargs={"poll_interval": 0.01}, daemon=True)
        thread.start()
        host, port = server.server_address
        try:
            # Reproduce the real failure shape: peers connect, begin an HTTP
            # request, then disappear before a response exists. Do enough cycles
            # to exceed the old 128-entry listen backlog several times.
            for _ in range(400):
                s = socket.create_connection((host, port), timeout=1.0)
                s.sendall(b"GET / HTTP/1.0\r\nHost: local\r\n")
                s.close()
            deadline = time.time() + 3.0
            while time.time() < deadline and server.metrics.active:
                time.sleep(0.01)
            with urllib.request.urlopen(f"http://{host}:{port}/", timeout=1.0) as response:
                self.assertEqual(response.read(), b"ok")
            self.assertEqual(server.metrics.public()["active"], 0)
            self.assertEqual(server.accept_failure_streak, 0)
        finally:
            server.shutdown()
            server.server_close()

    def test_fabric_store_closes_sqlite_connections(self):
        # SQLite Connection.__enter__/__exit__ commits transactions but does not
        # close the connection. Repeated Fabric polling must therefore use an
        # explicit closing() owner rather than depend on GC/finalizers.
        with tempfile.TemporaryDirectory() as td:
            store = FabricStore(Path(td) / "fabric.sqlite3")
            before = len(os.listdir("/proc/self/fd")) if os.path.isdir("/proc/self/fd") else None
            for _ in range(300):
                self.assertTrue(store.health()["ok"])
                store.events(since=0, limit=1)
            if before is not None:
                after = len(os.listdir("/proc/self/fd"))
                self.assertLessEqual(after, before + 4)

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
