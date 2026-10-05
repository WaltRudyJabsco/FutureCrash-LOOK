#!/usr/bin/env bash
set -euo pipefail
systemctl --user disable server-comfy.service server-mercury.service >/dev/null 2>&1 || true
rm -f "${HOME}/.config/systemd/user/server-comfy.service"
rm -f "${HOME}/.config/systemd/user/server-mercury.service"
systemctl --user daemon-reload || true
rm -f "${HOME}/.local/bin/server"
rm -rf "${HOME}/.local/share/3090-server"
echo "Controller removed. Existing applications/data were not removed."
