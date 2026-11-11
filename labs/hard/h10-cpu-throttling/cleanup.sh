#!/usr/bin/env bash
set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/../../../lib/common.sh"
systemctl disable --now traffic-replay >/dev/null 2>&1 || true
rm -f /etc/systemd/system/traffic-replay.service /usr/local/bin/traffic-replay
rm -rf /etc/systemd/system/shop.slice /etc/systemd/system/shop.slice.d
# install-base removes shopapp.service.d and restarts shopapp in system.slice
systemctl daemon-reload
restore_baseline
systemctl stop shop.slice 2>/dev/null || true
