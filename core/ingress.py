#!/usr/bin/env python3
"""Future Crash + LOOK Fabric ingress guard.

Runs in a separate process from the Unified Node. Tailscale Serve targets this
listener, which relays a bounded number of requests to the local node. Remote
connection pressure can therefore degrade ingress without taking down localhost
LO/Signal control traffic.
"""
from __future__ import annotations

import argparse
import faulthandler
import http.client
import json
import os
import signal
import socket
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlsplit

VERSION = "5.2.4"
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 7333
DEFAULT_BACKEND_HOST = "127.0.0.1"
DEFAULT_BACKEND_PORT = 7332
HEADER_TIMEOUT_SECONDS = 4.0
CONTROL_TIMEOUT_SECONDS = 12.0
STREAM_TIMEOUT_SECONDS = 240.0
MAX_ACTIVE_REQUESTS = 12
MAX_STREAM_REQUESTS = 4
MAX_BODY_BYTES = 8 * 1024 * 1024
WATCHDOG_STALE_SECONDS = 8.0

HOP_HEADERS = {
    "connection", "keep-alive", "proxy-authenticate", "proxy-authorization",
    "te", "trailers", "transfer-encoding", "upgrade",
}


def monotonic() -> float:
    return time.monotonic()


class Metrics:
    def __init__(self):
        self.lock = threading.RLock()
        self.accepted = 0
        self.active = 0
        self.started = 0
        self.completed = 0
        self.client_closed_early = 0
        self.rejected = 0
        self.errors = 0
        self.request_times = []
        self.peak_active = 0
        self.by_endpoint: dict[str, int] = {}
        self.last_error: str | None = None

    def on_accept(self):
        with self.lock:
            self.accepted += 1

    def on_start(self, method: str, path: str):
        with self.lock:
            self.active += 1
            self.started += 1
            stamp = monotonic()
            self.request_times.append(stamp)
            if len(self.request_times) > 4096:
                cutoff = stamp - 60.0
                self.request_times = [t for t in self.request_times if t >= cutoff]
            self.peak_active = max(self.peak_active, self.active)
            key = f"{method} {path}"
            self.by_endpoint[key] = self.by_endpoint.get(key, 0) + 1

    def on_finish(self):
        with self.lock:
            self.active = max(0, self.active - 1)
            self.completed += 1

    def on_client_closed(self):
        with self.lock:
            self.client_closed_early += 1

    def on_reject(self):
        with self.lock:
            self.rejected += 1

    def on_error(self, exc: BaseException):
        with self.lock:
            self.errors += 1
            self.last_error = f"{type(exc).__name__}: {exc}"[:240]

    def public(self):
        with self.lock:
            stamp = monotonic()
            recent_requests = sum(1 for ts in self.request_times if ts >= stamp - 60.0)
            return {
                "version": VERSION,
                "accepted": self.accepted,
                "connections_accepted": self.accepted,
                "requests_started": self.started,
                "connections_without_request": max(0, self.accepted - self.started - self.rejected),
                "requests_last_60s": recent_requests,
                "requests_per_sec_60s": round(recent_requests / 60.0, 3),
                "active": self.active,
                "completed": self.completed,
                "requests_completed": self.completed,
                "client_closed_early": self.client_closed_early,
                "rejected": self.rejected,
                "errors": self.errors,
                "peak_active": self.peak_active,
                "by_endpoint": dict(sorted(self.by_endpoint.items())),
                "last_error": self.last_error,
            }


METRICS = Metrics()


class GuardServer(ThreadingHTTPServer):
    request_queue_size = 64
    daemon_threads = True
    block_on_close = False
    allow_reuse_address = True

    def __init__(self, address, handler, backend_host: str, backend_port: int):
        self.backend_host = backend_host
        self.backend_port = backend_port
        self.request_slots = threading.BoundedSemaphore(MAX_ACTIVE_REQUESTS)
        self.stream_slots = threading.BoundedSemaphore(MAX_STREAM_REQUESTS)
        self.loop_heartbeat = monotonic()
        super().__init__(address, handler)

    def get_request(self):
        request, address = super().get_request()
        METRICS.on_accept()
        # Slow/incomplete backend connections from an edge proxy must not occupy
        # a request thread forever before an HTTP request even exists.
        request.settimeout(HEADER_TIMEOUT_SECONDS)
        return request, address

    def process_request(self, request, client_address):
        if not self.request_slots.acquire(blocking=False):
            METRICS.on_reject()
            try:
                request.close()
            finally:
                return
        try:
            return super().process_request(request, client_address)
        except Exception:
            self.request_slots.release()
            raise

    def process_request_thread(self, request, client_address):
        try:
            return super().process_request_thread(request, client_address)
        finally:
            self.request_slots.release()

    def service_actions(self):
        self.loop_heartbeat = monotonic()


class Handler(BaseHTTPRequestHandler):
    server_version = "FCLIngress/5.2.4"
    protocol_version = "HTTP/1.0"  # response EOF is the stream boundary; no keep-alive pool.

    def log_message(self, *args):
        pass

    def _send_json(self, code: int, obj):
        body = json.dumps(obj, separators=(",", ":")).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Connection", "close")
        self.end_headers()
        self.wfile.write(body)

    def _relay(self):
        parsed = urlsplit(self.path)
        path = parsed.path
        if path == "/_fcl/metrics":
            return self._send_json(200, {"ok": True, "ingress": METRICS.public()})
        if not (path == "/health" or path == "/v1/health" or path.startswith("/v1/")):
            return self._send_json(404, {"error": "not found"})

        METRICS.on_start(self.command, path)
        stream_slot = False
        conn = None
        try:
            is_stream = path == "/v1/infer/stream"
            if is_stream:
                stream_slot = self.server.stream_slots.acquire(blocking=False)
                if not stream_slot:
                    METRICS.on_reject()
                    return self._send_json(503, {"ok": False, "error": "Fabric ingress stream capacity busy"})

            length = int(self.headers.get("Content-Length", "0") or "0")
            if length < 0 or length > MAX_BODY_BYTES:
                return self._send_json(413, {"error": "request body too large"})
            body = self.rfile.read(length) if length else None

            headers = {}
            for key, value in self.headers.items():
                lk = key.lower()
                if lk in HOP_HEADERS or lk in {"host", "content-length"}:
                    continue
                headers[key] = value
            headers["Connection"] = "close"
            if body is not None:
                headers["Content-Length"] = str(len(body))

            timeout = STREAM_TIMEOUT_SECONDS if is_stream else CONTROL_TIMEOUT_SECONDS
            conn = http.client.HTTPConnection(self.server.backend_host, self.server.backend_port, timeout=timeout)
            target = parsed.path + (("?" + parsed.query) if parsed.query else "")
            conn.request(self.command, target, body=body, headers=headers)
            upstream = conn.getresponse()

            self.send_response(upstream.status, upstream.reason)
            for key, value in upstream.getheaders():
                lk = key.lower()
                if lk in HOP_HEADERS or lk in {"content-length"}:
                    continue
                self.send_header(key, value)
            self.send_header("Connection", "close")

            if is_stream:
                self.end_headers()
                while True:
                    chunk = upstream.read(8192)
                    if not chunk:
                        break
                    self.wfile.write(chunk)
                    self.wfile.flush()
            else:
                data = upstream.read()
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                if data:
                    self.wfile.write(data)
        except (BrokenPipeError, ConnectionResetError, socket.timeout):
            METRICS.on_client_closed()
        except Exception as exc:
            METRICS.on_error(exc)
            try:
                self._send_json(502, {"ok": False, "error": f"ingress backend failure: {exc}"})
            except Exception:
                pass
        finally:
            if conn is not None:
                try:
                    conn.close()
                except Exception:
                    pass
            if stream_slot:
                self.server.stream_slots.release()
            METRICS.on_finish()

    do_GET = _relay
    do_POST = _relay


def watchdog(server: GuardServer):
    while True:
        time.sleep(1.0)
        age = monotonic() - server.loop_heartbeat
        if age > WATCHDOG_STALE_SECONDS:
            print(f"FCL INGRESS · accept loop stalled for {age:.1f}s; terminating for service-manager recovery", file=sys.stderr, flush=True)
            faulthandler.dump_traceback(file=sys.stderr, all_threads=True)
            os._exit(70)


def main():
    ap = argparse.ArgumentParser(description="Future Crash + LOOK bounded Fabric ingress guard")
    ap.add_argument("--host", default=DEFAULT_HOST)
    ap.add_argument("--port", type=int, default=DEFAULT_PORT)
    ap.add_argument("--backend-host", default=DEFAULT_BACKEND_HOST)
    ap.add_argument("--backend-port", type=int, default=DEFAULT_BACKEND_PORT)
    ap.add_argument("--version", action="version", version=f"Future Crash + LOOK ingress {VERSION}")
    a = ap.parse_args()

    faulthandler.enable(all_threads=True)
    if hasattr(signal, "SIGUSR1"):
        faulthandler.register(signal.SIGUSR1, file=sys.stderr, all_threads=True)

    server = GuardServer((a.host, a.port), Handler, a.backend_host, a.backend_port)
    threading.Thread(target=watchdog, args=(server,), name="ingress-watchdog", daemon=True).start()
    print(f"Future Crash + LOOK ingress {VERSION} · http://{a.host}:{a.port} → http://{a.backend_host}:{a.backend_port}", flush=True)
    try:
        server.serve_forever(poll_interval=.2)
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
