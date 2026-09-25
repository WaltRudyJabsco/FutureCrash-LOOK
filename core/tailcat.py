#!/usr/bin/env python3
"""Tailcat: native encrypted Fabric transport.

Phase 1 deliberately does not replace discovery or NAT traversal. It gives already
paired Fabric nodes a direct TLS transport on ordinary reachable IP addresses, with
exact certificate pinning learned during pairing. Tailscale remains a fallback.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import socket
import ssl
import subprocess
import tempfile
import threading
import time
from pathlib import Path

try:
    from .ingress import GuardServer, Handler, watchdog
except ImportError:
    from ingress import GuardServer, Handler, watchdog

VERSION = "6.3.2"
DEFAULT_HOST = "0.0.0.0"
DEFAULT_PORT = 7443
DEFAULT_BACKEND_HOST = "127.0.0.1"
DEFAULT_BACKEND_PORT = 7332
STATE_ROOT = Path.home() / ".config/future-crash-look/tailcat"
KEY_PATH = STATE_ROOT / "tls-key.pem"
CERT_PATH = STATE_ROOT / "tls-cert.pem"
AD_PATH = STATE_ROOT / "advertisement.json"


def _atomic_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=path.name + ".", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(data, fh, indent=2, sort_keys=True)
            fh.write("\n")
        os.chmod(tmp, 0o600)
        os.replace(tmp, path)
    finally:
        try: os.unlink(tmp)
        except FileNotFoundError: pass


def _local_ipv4() -> list[str]:
    values = set()
    try:
        for item in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET):
            addr = str(item[4][0])
            if addr and not addr.startswith("127.") and addr != "0.0.0.0":
                values.add(addr)
    except OSError:
        pass
    # No packet is sent; connect() simply asks the kernel which source address it
    # would use. This catches Wi-Fi/Ethernet addresses absent from hostname DNS.
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 53))
        addr = s.getsockname()[0]
        if addr and not addr.startswith("127."):
            values.add(addr)
    except OSError:
        pass
    finally:
        s.close()
    return sorted(values)


def _cert_fingerprint(cert_pem: str) -> str:
    der = ssl.PEM_cert_to_DER_cert(cert_pem)
    digest = hashlib.sha256(der).hexdigest()
    return ":".join(digest[i:i+2] for i in range(0, len(digest), 2))


def ensure_identity(port: int = DEFAULT_PORT) -> dict:
    STATE_ROOT.mkdir(parents=True, exist_ok=True)
    try: STATE_ROOT.chmod(0o700)
    except OSError: pass
    if not (KEY_PATH.exists() and CERT_PATH.exists()):
        openssl = shutil.which("openssl")
        if not openssl:
            raise RuntimeError("Tailcat TLS requires openssl")
        cfg = STATE_ROOT / "openssl.cnf"
        cfg.write_text("""[req]\nprompt = no\ndistinguished_name = dn\nx509_extensions = v3\n[dn]\nCN = Future Crash LOOK Tailcat\n[v3]\nbasicConstraints = critical,CA:TRUE\nkeyUsage = critical,digitalSignature,keyEncipherment,keyCertSign\nextendedKeyUsage = serverAuth\nsubjectKeyIdentifier = hash\n""", encoding="utf-8")
        proc = subprocess.run([
            openssl, "req", "-x509", "-newkey", "rsa:2048", "-nodes",
            "-keyout", str(KEY_PATH), "-out", str(CERT_PATH), "-days", "3650",
            "-config", str(cfg),
        ], capture_output=True, text=True, timeout=20)
        try: cfg.unlink()
        except OSError: pass
        if proc.returncode:
            raise RuntimeError((proc.stderr or proc.stdout or "openssl certificate generation failed").strip())
        KEY_PATH.chmod(0o600); CERT_PATH.chmod(0o644)
    cert = CERT_PATH.read_text(encoding="utf-8")
    host=socket.gethostname().strip().rstrip(".")
    endpoints=[]
    if host:
        endpoints.append(f"https://{host}.local:{int(port)}")
    endpoints.extend(f"https://{ip}:{int(port)}" for ip in _local_ipv4())
    endpoints=list(dict.fromkeys(endpoints))
    ad = {
        "schema": "tailcat-transport-v1",
        "version": VERSION,
        "port": int(port),
        "endpoints": endpoints,
        "cert_pem": cert,
        "cert_sha256": _cert_fingerprint(cert),
    }
    _atomic_json(AD_PATH, ad)
    return ad


def advertisement() -> dict:
    try:
        data = json.loads(AD_PATH.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _advertisement_loop(port: int):
    while True:
        time.sleep(30.0)
        try: ensure_identity(port)
        except Exception: pass


def main() -> int:
    ap = argparse.ArgumentParser(description="Future Crash + LOOK Tailcat native TLS transport")
    ap.add_argument("command", nargs="?", default="serve", choices=["serve", "init", "show"])
    ap.add_argument("--host", default=DEFAULT_HOST)
    ap.add_argument("--port", type=int, default=DEFAULT_PORT)
    ap.add_argument("--backend-host", default=DEFAULT_BACKEND_HOST)
    ap.add_argument("--backend-port", type=int, default=DEFAULT_BACKEND_PORT)
    ap.add_argument("--version", action="version", version=f"Future Crash + LOOK Tailcat {VERSION}")
    a = ap.parse_args()
    if a.command == "init":
        print(json.dumps(ensure_identity(a.port), indent=2)); return 0
    if a.command == "show":
        print(json.dumps(advertisement() or ensure_identity(a.port), indent=2)); return 0

    ad = ensure_identity(a.port)
    server = GuardServer((a.host, a.port), Handler, a.backend_host, a.backend_port)
    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    ctx.minimum_version = ssl.TLSVersion.TLSv1_2
    ctx.load_cert_chain(str(CERT_PATH), str(KEY_PATH))
    server.socket = ctx.wrap_socket(server.socket, server_side=True)
    threading.Thread(target=watchdog, args=(server,), name="tailcat-watchdog", daemon=True).start()
    threading.Thread(target=_advertisement_loop, args=(a.port,), name="tailcat-address-refresh", daemon=True).start()
    eps = ", ".join(ad.get("endpoints") or []) or f"https://{a.host}:{a.port}"
    print(f"Future Crash + LOOK Tailcat {VERSION} · {eps} → http://{a.backend_host}:{a.backend_port}", flush=True)
    try:
        server.serve_forever(poll_interval=.2)
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
