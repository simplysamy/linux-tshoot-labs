#!/usr/bin/env bash
set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/../../../lib/common.sh"
systemctl disable --now legacy-status >/dev/null 2>&1 || true
rm -f /etc/systemd/system/legacy-status.service
rm -rf /var/www/legacy-status
systemctl daemon-reload
restore_baseline
