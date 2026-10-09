#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

pick_python() {
  local candidate

  # Prefer an explicitly supplied interpreter.
  if [[ -n "${FC_PYTHON:-}" ]]; then
    if "$FC_PYTHON" -c 'import pytest' >/dev/null 2>&1; then
      printf '%s\n' "$FC_PYTHON"
      return 0
    fi
    echo "FC_PYTHON=$FC_PYTHON does not have pytest installed" >&2
    return 1
  fi

  # Use the first normal interpreter that can actually run the suite.
  for candidate in python3 python python3.13 python3.12 python3.11; do
    if command -v "$candidate" >/dev/null 2>&1 &&
       "$candidate" -c 'import pytest' >/dev/null 2>&1; then
      printf '%s\n' "$candidate"
      return 0
    fi
  done

  return 1
}

PYTHON="$(pick_python || true)"

if [[ -z "$PYTHON" ]]; then
  echo "ERROR: no Python interpreter with pytest installed was found." >&2
  echo "Available Python interpreters:" >&2
  command -v python3 2>/dev/null || true
  command -v python 2>/dev/null || true
  command -v python3.13 2>/dev/null || true
  command -v python3.12 2>/dev/null || true
  command -v python3.11 2>/dev/null || true
  exit 1
fi

echo "Future Crash + LOOK · verify"
echo "──────────────────────────"
echo "python: $("$PYTHON" -c 'import sys; print(sys.executable)')"
echo "version: $("$PYTHON" -c 'import sys; print(sys.version.split()[0])')"

echo "[1/5] structural health"
"$PYTHON" tools/code_health.py --check >/dev/null
"$PYTHON" tools/command_reference.py --check

echo "[2/5] Python syntax"
"$PYTHON" -m compileall -q \
  look core albert future-crash local-labs-host signal-window tools
"$PYTHON" -m py_compile look/lk

# The development venv can be newer than endpoint Python. Parse `lk` using the
# oldest grammar we support so a new nested-f-string feature cannot break Macs
# while passing verification on the Linux development machine.
"$PYTHON" - <<'PYGRAMMAR'
import ast
from pathlib import Path

source=Path("look/lk").read_text()
ast.parse(source,filename="look/lk",feature_version=(3,10))
PYGRAMMAR

echo "[3/5] shell syntax"
for script in \
  install.sh \
  install-look.sh \
  albert/install.sh \
  signal-window/install.sh
do
  [[ -f "$script" ]] && bash -n "$script"
done

echo "[4/5] JavaScript syntax"
if command -v node >/dev/null 2>&1; then
  for script in signal-window/app.js; do
    [[ -f "$script" ]] && node --check "$script" >/dev/null
  done
else
  echo "  node unavailable · skipped"
fi

echo "[5/5] regression suite"
"$PYTHON" -m pytest -q

echo "VERIFY OK"
