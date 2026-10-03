#!/usr/bin/env python3
"""Own the Future Crash slice of Tailscale Serve without resetting other routes.

Future Crash uses several HTTPS ports on one node.  Configure them from one place
so independent installers cannot fight over Tailscale's persistent Serve state.
Only the ports listed in MANAGED_ROUTES are touched; unrelated Serve/Funnel state
is deliberately left alone.
"""
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Sequence

VERSION = "8.5.4"


@dataclass(frozen=True)
class Route:
    name: str
    https_port: int
    backend: str


MANAGED_ROUTES: tuple[Route, ...] = (
    Route("Albert", 7330, "http://127.0.0.1:7330"),
    Route("Signal", 7331, "http://127.0.0.1:7331"),
    Route("Node API", 7332, "http://127.0.0.1:7333"),
)


def tailscale_binary() -> str | None:
    found = shutil.which("tailscale")
    if found:
        return found
    for candidate in (
        "/opt/homebrew/bin/tailscale",
        "/usr/local/bin/tailscale",
        "/Applications/Tailscale.app/Contents/MacOS/Tailscale",
        "/Applications/Tailscale.app/Contents/MacOS/tailscale",
    ):
        if Path(candidate).is_file() and os.access(candidate, os.X_OK):
            return candidate
    return None


def _run(argv: Sequence[str], *, timeout: float = 12.0) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        list(argv), text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        timeout=timeout, check=False,
    )


def _as_sudo(argv: Sequence[str]) -> list[str]:
    sudo = shutil.which("sudo")
    return [sudo, "-n", *argv] if sudo else list(argv)


def _attempt(argv: Sequence[str]) -> tuple[bool, str]:
    cp = _run(argv)
    detail = (cp.stderr or cp.stdout or "").strip()
    if cp.returncode == 0:
        return True, detail
    # Some installs have Tailscale's operator owned by root.  Never prompt here;
    # the installer should remain deterministic and print a single repair command.
    sudo_argv = _as_sudo(argv)
    if list(sudo_argv) != list(argv):
        cp2 = _run(sudo_argv)
        detail2 = (cp2.stderr or cp2.stdout or "").strip()
        if cp2.returncode == 0:
            return True, detail2
        detail = detail2 or detail
    return False, detail



def backend_ready(binary: str) -> tuple[bool, str]:
    """Return whether the Tailscale networking backend is actually running."""
    cp = _run([binary, "status", "--json"], timeout=5.0)
    text = (cp.stderr or cp.stdout or "").strip()
    if cp.returncode != 0:
        return False, text or "Tailscale status unavailable"
    try:
        import json
        data = json.loads(cp.stdout or "{}")
        state = str(data.get("BackendState") or "").casefold()
        online = bool((data.get("Self") or {}).get("Online", False))
        return state == "running" or online, state or "offline"
    except Exception:
        return True, "status available"


def ensure_backend(binary: str) -> tuple[bool, str]:
    """Wake Tailscale before reconciling routes. A stopped VPN is not a Fabric bug."""
    ok, detail = backend_ready(binary)
    if ok:
        return True, detail
    if sys.platform == "darwin":
        opener = shutil.which("open") or "/usr/bin/open"
        _run([opener, "-gja", "Tailscale"], timeout=8.0)
        for _ in range(30):
            time.sleep(0.25)
            ok, detail = backend_ready(binary)
            if ok:
                return True, detail
        return False, detail or "Tailscale app did not start"
    # Linux installations normally run tailscaled as a system service. Try the
    # non-interactive service path; never block an installer on a sudo prompt.
    systemctl = shutil.which("systemctl")
    if systemctl:
        _run(_as_sudo([systemctl, "start", "tailscaled"]), timeout=8.0)
        for _ in range(12):
            time.sleep(0.25)
            ok, detail = backend_ready(binary)
            if ok:
                return True, detail
    return False, detail or "Tailscale backend is stopped"


def set_route(binary: str, route: Route) -> tuple[bool, str]:
    desired = [
        binary, "serve", "--bg", "--yes",
        f"--https={route.https_port}", route.backend,
    ]
    ok, detail = _attempt(desired)
    if ok:
        return True, detail

    # Reconcile an old backend on OUR port only.  Do not use `serve reset`:
    # users may have unrelated Tailscale services on this machine.
    off = [binary, "serve", "--yes", f"--https={route.https_port}", "off"]
    off_ok, off_detail = _attempt(off)
    if not off_ok:
        return False, detail or off_detail
    return _attempt(desired)


def status(binary: str) -> tuple[bool, str]:
    cp = _run([binary, "serve", "status"], timeout=8.0)
    return cp.returncode == 0, (cp.stdout or cp.stderr or "").strip()


def reconcile(binary: str, routes: Iterable[Route] = MANAGED_ROUTES) -> tuple[bool, list[str], str]:
    messages: list[str] = []
    all_ok = True
    for route in routes:
        ok, detail = set_route(binary, route)
        all_ok = all_ok and ok
        if ok:
            messages.append(f"{route.name}: :{route.https_port} → {route.backend}")
        else:
            short = detail.splitlines()[-1] if detail else "Tailscale rejected the route"
            messages.append(f"{route.name}: FAILED · {short}")
    status_ok, serve_status = status(binary)
    # Successful mutation commands are not enough: confirm Tailscale persisted
    # every managed port/backend pair before the installer declares victory.
    verified = status_ok and all(
        f":{route.https_port}" in serve_status and route.backend in serve_status
        for route in routes
    )
    if status_ok and not verified:
        messages.append("verification: FAILED · persisted Serve state does not match requested routes")
    return all_ok and verified, messages, serve_status


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Reconcile Future Crash Tailscale Serve routes")
    parser.add_argument("--status", action="store_true", help="show current Serve state only")
    args = parser.parse_args(argv)
    binary = tailscale_binary()
    if not binary:
        # Tailscale remains optional; LAN/Tailcat transport can still operate.
        print("Tailscale Serve: tailscale CLI not found · skipped")
        return 0
    if args.status:
        ok, text = status(binary)
        print(text or "Tailscale Serve: no routes")
        return 0 if ok else 4

    backend_ok, backend_detail = ensure_backend(binary)
    if not backend_ok:
        print(f"Tailscale backend: FAILED · {backend_detail}")
        return 6
    print(f"Tailscale backend: ready · {backend_detail}")
    ok, messages, serve_status = reconcile(binary)
    print("Future Crash Tailscale Serve")
    for message in messages:
        print(f"  {message}")
    if not ok:
        print("  current Serve state:")
        for line in (serve_status or "unavailable").splitlines():
            print(f"    {line}")
        print("  repair once with administrator permission:")
        for route in MANAGED_ROUTES:
            print(
                f"    sudo {binary} serve --bg --yes --https={route.https_port} {route.backend}"
            )
        return 5
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
