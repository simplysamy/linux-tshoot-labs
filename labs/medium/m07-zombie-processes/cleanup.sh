#!/usr/bin/env bash
set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/../../../lib/common.sh"
systemctl disable --now queue-dispatcher >/dev/null 2>&1 || true
rm -rf /etc/systemd/system/queue-dispatcher.service /etc/systemd/system/queue-dispatcher.service.d \
       /usr/local/bin/queue-dispatcher /etc/queue-dispatcher.conf
systemctl daemon-reload
systemctl reset-failed queue-dispatcher 2>/dev/null || true
restore_baseline
